import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import json
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
from collections import Counter

from app.db.crud.feedback import get_feedbacks_by_criteria, get_feedbacks_by_query
from app.db.crud.users import get_user_by_id
from app.services.feedback_analyzer import analyze_feedback
from app.core.config import settings

logger = logging.getLogger(__name__)

class FeedbackScorer:
    """Service for scoring and analyzing user feedback."""
    
    def __init__(self):
        """Initialize the feedback scorer."""
        self.rating_weight = 0.6
        self.helpful_weight = 0.4
        self.min_samples = 5
    
    async def score_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score an individual feedback entry.
        
        Args:
            feedback_data: The feedback data to score
            
        Returns:
            The score and analysis
        """
        score = 0.0
        score_components = {}
        
        # Score based on rating (1-5)
        rating = feedback_data.get("rating")
        if rating is not None:
            rating_score = (rating - 1) / 4  # Normalize to 0-1
            score += rating_score * self.rating_weight
            score_components["rating"] = {
                "raw_value": rating,
                "normalized_value": rating_score,
                "weight": self.rating_weight,
                "contribution": rating_score * self.rating_weight
            }
        
        # Score based on helpful flag
        helpful = feedback_data.get("helpful")
        if helpful is not None:
            helpful_score = 1.0 if helpful else 0.0
            score += helpful_score * self.helpful_weight
            score_components["helpful"] = {
                "raw_value": helpful,
                "normalized_value": helpful_score,
                "weight": self.helpful_weight,
                "contribution": helpful_score * self.helpful_weight
            }
        
        # Text sentiment analysis would be added here in a real implementation
        # For now we just check for the presence of feedback text
        feedback_text = feedback_data.get("feedback_text")
        has_text_feedback = feedback_text is not None and len(feedback_text.strip()) > 0
        
        # Additional indicators
        missing_info = feedback_data.get("missing_information", False)
        selected_sources = feedback_data.get("selected_sources", [])
        has_source_selection = len(selected_sources) > 0
        
        # Aggregate score and analysis
        result = {
            "score": score,
            "score_components": score_components,
            "has_text_feedback": has_text_feedback,
            "missing_information": missing_info,
            "has_source_selection": has_source_selection,
            "selected_sources_count": len(selected_sources),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return result
    
    async def aggregate_feedback(
        self,
        query_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate feedback based on criteria.
        
        Args:
            query_id: Optional query ID to filter by
            start_date: Optional start date
            end_date: Optional end date
            user_id: Optional user ID
            model_name: Optional model name
            
        Returns:
            Aggregated feedback statistics and scores
        """
        # Build query criteria
        criteria = {}
        if query_id:
            criteria["query_id"] = query_id
        if user_id:
            criteria["user_id"] = user_id
        if model_name:
            criteria["model_name"] = model_name
        
        # Date range
        if start_date or end_date:
            criteria["timestamp"] = {}
            if start_date:
                criteria["timestamp"]["$gte"] = start_date
            if end_date:
                criteria["timestamp"]["$lte"] = end_date
        
        # Get feedbacks
        feedbacks = await get_feedbacks_by_criteria(criteria)
        
        # Return early if no feedbacks
        if not feedbacks:
            return {
                "count": 0,
                "average_score": 0,
                "average_rating": 0,
                "helpful_percentage": 0,
                "has_feedback_text_percentage": 0,
                "missing_information_percentage": 0,
                "source_selection_percentage": 0,
                "criteria": criteria,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Calculate aggregated scores
        total_score = 0
        total_rating = 0
        helpful_count = 0
        text_feedback_count = 0
        missing_info_count = 0
        source_selection_count = 0
        
        for feedback in feedbacks:
            # Score the feedback
            score_result = await self.score_feedback(feedback)
            total_score += score_result["score"]
            
            # Rating
            if "rating" in feedback and feedback["rating"] is not None:
                total_rating += feedback["rating"]
            
            # Helpful flag
            if "helpful" in feedback and feedback["helpful"] is True:
                helpful_count += 1
            
            # Text feedback
            if "feedback_text" in feedback and feedback["feedback_text"] and len(feedback["feedback_text"].strip()) > 0:
                text_feedback_count += 1
            
            # Missing information
            if "missing_information" in feedback and feedback["missing_information"] is True:
                missing_info_count += 1
            
            # Source selection
            if "selected_sources" in feedback and feedback["selected_sources"] and len(feedback["selected_sources"]) > 0:
                source_selection_count += 1
        
        # Calculate averages and percentages
        count = len(feedbacks)
        average_score = total_score / count
        average_rating = total_rating / count if total_rating > 0 else 0
        helpful_percentage = (helpful_count / count) * 100
        text_feedback_percentage = (text_feedback_count / count) * 100
        missing_info_percentage = (missing_info_count / count) * 100
        source_selection_percentage = (source_selection_count / count) * 100
        
        # Return aggregated results
        return {
            "count": count,
            "average_score": average_score,
            "average_rating": average_rating,
            "helpful_percentage": helpful_percentage,
            "has_feedback_text_percentage": text_feedback_percentage,
            "missing_information_percentage": missing_info_percentage,
            "source_selection_percentage": source_selection_percentage,
            "criteria": criteria,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def generate_feedback_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_name: Optional[str] = None,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive feedback report.
        
        Args:
            start_date: Optional start date
            end_date: Optional end date
            model_name: Optional model name
            output_format: Output format (json or html)
            
        Returns:
            A comprehensive feedback report
        """
        # Default time range if not specified
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Build criteria
        criteria = {}
        if model_name:
            criteria["model_name"] = model_name
        
        # Date range
        criteria["timestamp"] = {}
        criteria["timestamp"]["$gte"] = start_date
        criteria["timestamp"]["$lte"] = end_date
        
        # Get all feedbacks in the time range
        feedbacks = await get_feedbacks_by_criteria(criteria)
        
        # Return early if no feedbacks
        if not feedbacks:
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "model_name": model_name,
                "total_feedbacks": 0,
                "message": "No feedback data available for the specified criteria"
            }
        
        # Calculate overall statistics
        overall_stats = await self.aggregate_feedback(
            start_date=start_date,
            end_date=end_date,
            model_name=model_name
        )
        
        # Create a pandas DataFrame for analysis
        df = pd.DataFrame(feedbacks)
        
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Group by date and calculate daily metrics
        daily_metrics = []
        if 'timestamp' in df.columns:
            df['date'] = df['timestamp'].dt.date
            daily_counts = df.groupby('date').size()
            daily_ratings = df.groupby('date')['rating'].mean()
            
            for date in sorted(daily_counts.index):
                count = daily_counts.get(date, 0)
                avg_rating = daily_ratings.get(date, 0)
                
                daily_metrics.append({
                    "date": date.isoformat(),
                    "count": int(count),
                    "average_rating": float(avg_rating)
                })
        
        # Top tags analysis
        top_tags = []
        if 'tags' in df.columns:
            all_tags = []
            for tags_list in df['tags'].dropna():
                if isinstance(tags_list, list):
                    all_tags.extend(tags_list)
            
            tag_counter = Counter(all_tags)
            top_tags = [{"tag": tag, "count": count} for tag, count in tag_counter.most_common(10)]
        
        # Feedback text analysis
        text_samples = []
        if 'feedback_text' in df.columns:
            texts = df['feedback_text'].dropna()
            if not texts.empty:
                # Sample some feedback texts (positive and negative)
                positive_texts = df[df['rating'] >= 4]['feedback_text'].dropna()
                negative_texts = df[df['rating'] <= 2]['feedback_text'].dropna()
                
                pos_samples = positive_texts.sample(min(5, len(positive_texts))).tolist() if not positive_texts.empty else []
                neg_samples = negative_texts.sample(min(5, len(negative_texts))).tolist() if not negative_texts.empty else []
                
                text_samples = {
                    "positive": pos_samples,
                    "negative": neg_samples
                }
        
        # Source selection analysis
        source_analysis = {}
        if 'selected_sources' in df.columns:
            all_sources = []
            for sources_list in df['selected_sources'].dropna():
                if isinstance(sources_list, list):
                    all_sources.extend(sources_list)
            
            source_counter = Counter(all_sources)
            top_sources = [{"source_id": src, "count": count} for src, count in source_counter.most_common(10)]
            source_analysis = {
                "top_sources": top_sources,
                "selection_rate": overall_stats["source_selection_percentage"]
            }
        
        # Generate charts for the report if requested
        charts = {}
        if output_format == "html":
            try:
                # Rating distribution chart
                if 'rating' in df.columns:
                    rating_counts = df['rating'].value_counts().sort_index()
                    plt.figure(figsize=(8, 5))
                    bars = plt.bar(rating_counts.index, rating_counts.values)
                    plt.title('Rating Distribution')
                    plt.xlabel('Rating')
                    plt.ylabel('Count')
                    plt.xticks(range(1, 6))
                    
                    # Add count labels above bars
                    for bar in bars:
                        height = bar.get_height()
                        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                f'{int(height)}', ha='center', va='bottom')
                    
                    # Save to base64
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png')
                    buffer.seek(0)
                    rating_chart = base64.b64encode(buffer.read()).decode('utf-8')
                    charts["rating_distribution"] = f"data:image/png;base64,{rating_chart}"
                    plt.close()
                
                # Daily feedback counts chart
                if daily_metrics:
                    dates = [datetime.fromisoformat(m['date']) for m in daily_metrics]
                    counts = [m['count'] for m in daily_metrics]
                    ratings = [m['average_rating'] for m in daily_metrics]
                    
                    plt.figure(figsize=(10, 6))
                    
                    # Plot counts
                    ax1 = plt.gca()
                    ax1.bar(dates, counts, color='skyblue', alpha=0.7)
                    ax1.set_xlabel('Date')
                    ax1.set_ylabel('Feedback Count', color='skyblue')
                    ax1.tick_params(axis='y', labelcolor='skyblue')
                    
                    # Plot ratings on secondary y-axis
                    ax2 = ax1.twinx()
                    ax2.plot(dates, ratings, color='red', marker='o', linestyle='-')
                    ax2.set_ylabel('Average Rating', color='red')
                    ax2.tick_params(axis='y', labelcolor='red')
                    ax2.set_ylim(0, 5.5)
                    
                    plt.title('Daily Feedback Counts and Average Ratings')
                    plt.tight_layout()
                    
                    # Save to base64
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png')
                    buffer.seek(0)
                    daily_chart = base64.b64encode(buffer.read()).decode('utf-8')
                    charts["daily_metrics"] = f"data:image/png;base64,{daily_chart}"
                    plt.close()
            
            except Exception as e:
                logger.error(f"Error generating charts: {str(e)}")
                charts["error"] = str(e)
        
        # Compile final report
        report = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "model_name": model_name,
            "total_feedbacks": len(feedbacks),
            "overall_stats": overall_stats,
            "daily_metrics": daily_metrics,
            "top_tags": top_tags,
            "text_samples": text_samples,
            "source_analysis": source_analysis
        }
        
        if charts:
            report["charts"] = charts
        
        return report
    
    async def track_feedback_trends(
        self,
        time_periods: List[Tuple[datetime, datetime]],
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track feedback trends across multiple time periods.
        
        Args:
            time_periods: List of (start_date, end_date) tuples
            model_name: Optional model name to filter by
            
        Returns:
            Feedback trends across the time periods
        """
        trends = []
        
        for start_date, end_date in time_periods:
            stats = await self.aggregate_feedback(
                start_date=start_date,
                end_date=end_date,
                model_name=model_name
            )
            
            trend_point = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "count": stats["count"],
                "average_rating": stats["average_rating"],
                "helpful_percentage": stats["helpful_percentage"]
            }
            
            trends.append(trend_point)
        
        # Calculate trend changes
        changes = {}
        if len(trends) >= 2:
            first = trends[0]
            last = trends[-1]
            
            changes = {
                "count_change": last["count"] - first["count"],
                "count_change_percentage": ((last["count"] / first["count"]) - 1) * 100 if first["count"] > 0 else None,
                "rating_change": last["average_rating"] - first["average_rating"],
                "helpful_change": last["helpful_percentage"] - first["helpful_percentage"]
            }
        
        return {
            "time_periods": len(time_periods),
            "trends": trends,
            "changes": changes,
            "model_name": model_name
        }
    
    async def compare_models(
        self,
        model_names: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Compare feedback between different models.
        
        Args:
            model_names: List of model names to compare
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Comparison of feedback between models
        """
        comparison = []
        
        for model_name in model_names:
            stats = await self.aggregate_feedback(
                start_date=start_date,
                end_date=end_date,
                model_name=model_name
            )
            
            model_stats = {
                "model_name": model_name,
                "count": stats["count"],
                "average_rating": stats["average_rating"],
                "helpful_percentage": stats["helpful_percentage"],
                "missing_information_percentage": stats["missing_information_percentage"]
            }
            
            comparison.append(model_stats)
        
        # Sort by average rating descending
        comparison.sort(key=lambda x: x["average_rating"], reverse=True)
        
        return {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "models_compared": len(model_names),
            "comparison": comparison
        }
    
    async def analyze_user_feedback_patterns(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze feedback patterns for a specific user.
        
        Args:
            user_id: The user ID
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Analysis of user feedback patterns
        """
        # Get user information
        user = await get_user_by_id(user_id)
        if not user:
            return {
                "error": f"User not found: {user_id}"
            }
        
        # Get user's feedback
        stats = await self.aggregate_feedback(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get global stats for the same period for comparison
        global_stats = await self.aggregate_feedback(
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate differences from global average
        differences = {
            "rating_diff": stats["average_rating"] - global_stats["average_rating"],
            "helpful_diff": stats["helpful_percentage"] - global_stats["helpful_percentage"],
            "text_feedback_diff": stats["has_feedback_text_percentage"] - global_stats["has_feedback_text_percentage"],
            "missing_info_diff": stats["missing_information_percentage"] - global_stats["missing_information_percentage"]
        }
        
        # Generate user pattern insights
        insights = []
        
        if stats["count"] > 0:
            if differences["rating_diff"] <= -0.5:
                insights.append("User tends to rate lower than average")
            elif differences["rating_diff"] >= 0.5:
                insights.append("User tends to rate higher than average")
            
            if differences["helpful_diff"] <= -10:
                insights.append("User marks helpful less often than average")
            elif differences["helpful_diff"] >= 10:
                insights.append("User marks helpful more often than average")
            
            if differences["text_feedback_diff"] >= 10:
                insights.append("User provides text feedback more frequently than average")
            
            if differences["missing_info_diff"] >= 10:
                insights.append("User reports missing information more often than average")
        
        return {
            "user_id": user_id,
            "user_name": user.get("name", "Unknown"),
            "feedback_count": stats["count"],
            "user_stats": stats,
            "global_comparison": {
                "global_stats": global_stats,
                "differences": differences
            },
            "insights": insights
        }
    
    async def generate_model_improvement_recommendations(
        self,
        model_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_feedback_count: int = 50
    ) -> Dict[str, Any]:
        """
        Generate improvement recommendations for a model based on feedback.
        
        Args:
            model_name: The model name
            start_date: Optional start date
            end_date: Optional end date
            min_feedback_count: Minimum feedback count required for reliable recommendations
            
        Returns:
            Improvement recommendations for the model
        """
        # Get model feedback stats
        stats = await self.aggregate_feedback(
            model_name=model_name,
            start_date=start_date,
            end_date=end_date
        )
        
        # Return early if not enough feedback
        if stats["count"] < min_feedback_count:
            return {
                "model_name": model_name,
                "feedback_count": stats["count"],
                "min_required": min_feedback_count,
                "message": f"Not enough feedback for reliable recommendations (need at least {min_feedback_count})"
            }
        
        # Get all feedback data for detailed analysis
        criteria = {"model_name": model_name}
        if start_date or end_date:
            criteria["timestamp"] = {}
            if start_date:
                criteria["timestamp"]["$gte"] = start_date
            if end_date:
                criteria["timestamp"]["$lte"] = end_date
        
        feedbacks = await get_feedbacks_by_criteria(criteria)
        
        # Extract text feedback for content analysis
        low_rating_feedback = [f for f in feedbacks if f.get("rating", 0) <= 2 and f.get("feedback_text")]
        missing_info_feedback = [f for f in feedbacks if f.get("missing_information") is True]
        
        # Perform basic text analysis
        # In a real implementation, this would use more sophisticated NLP techniques
        improvement_areas = []
        common_issues = []
        
        # Analyze low rating feedback
        if low_rating_feedback:
            improvement_areas.append({
                "area": "Low Rating Responses",
                "count": len(low_rating_feedback),
                "percentage": (len(low_rating_feedback) / stats["count"]) * 100,
                "sample_count": min(3, len(low_rating_feedback)),
                "samples": [f.get("feedback_text") for f in low_rating_feedback[:3]]
            })
        
        # Analyze missing information feedback
        if missing_info_feedback:
            improvement_areas.append({
                "area": "Missing Information",
                "count": len(missing_info_feedback),
                "percentage": (len(missing_info_feedback) / stats["count"]) * 100,
                "sample_count": min(3, len(missing_info_feedback)),
                "samples": [f.get("feedback_text") for f in missing_info_feedback[:3] if f.get("feedback_text")]
            })
        
        # Generate recommendations
        recommendations = []
        
        if stats["average_rating"] < 3.5:
            recommendations.append({
                "priority": "High",
                "recommendation": "Improve overall response quality",
                "rationale": f"Average rating is low ({stats['average_rating']:.1f}/5.0)",
                "suggested_action": "Review low-rated responses for common patterns and fine-tune the model"
            })
        
        if stats["missing_information_percentage"] > 20:
            recommendations.append({
                "priority": "Medium",
                "recommendation": "Enhance information completeness",
                "rationale": f"{stats['missing_information_percentage']:.1f}% of feedback indicates missing information",
                "suggested_action": "Improve knowledge base and context handling"
            })
        
        if stats["helpful_percentage"] < 70:
            recommendations.append({
                "priority": "Medium",
                "recommendation": "Improve response helpfulness",
                "rationale": f"Only {stats['helpful_percentage']:.1f}% of responses were marked as helpful",
                "suggested_action": "Fine-tune for more actionable and directly useful responses"
            })
        
        # Determine if fine-tuning is recommended
        fine_tuning_recommended = (
            stats["count"] >= 100 and
            (stats["average_rating"] < 4.0 or stats["helpful_percentage"] < 75)
        )
        
        return {
            "model_name": model_name,
            "feedback_count": stats["count"],
            "stats": stats,
            "improvement_areas": improvement_areas,
            "common_issues": common_issues,
            "recommendations": recommendations,
            "fine_tuning_recommended": fine_tuning_recommended,
            "generated_at": datetime.utcnow().isoformat()
        }


# Singleton instance
_feedback_scorer = None

def get_feedback_scorer() -> FeedbackScorer:
    """Get the feedback scorer singleton."""
    global _feedback_scorer
    if _feedback_scorer is None:
        _feedback_scorer = FeedbackScorer()
    return _feedback_scorer
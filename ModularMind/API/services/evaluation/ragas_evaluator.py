"""
RAGAS tabanlı RAG değerlendirme modülü.
RAG sisteminin kalitesini çeşitli metriklerle ölçer.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Union
import uuid
import json
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class RAGASEvaluator:
    """
    RAGAS tabanlı RAG değerlendirme sınıfı.
    """

    def __init__(self, llm_service=None, embedding_service=None):
        """
        Args:
            llm_service: LLM servisi
            embedding_service: Embedding servisi
        """
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self._setup_ragas()
        
    def _setup_ragas(self):
        """RAGAS'ı başlatır."""
        try:
            from ragas.metrics import (
                faithfulness,
                answer_relevancy, 
                context_relevancy,
                context_precision,
                context_recall
            )
            from ragas.metrics.critique import harmfulness
            
            self.metrics = {
                "faithfulness": faithfulness,
                "answer_relevancy": answer_relevancy,
                "context_relevancy": context_relevancy,
                "context_precision": context_precision,
                "context_recall": context_recall,
                "harmfulness": harmfulness
            }
            
            self.ragas_available = True
            logger.info("RAGAS başarıyla yüklendi")
            
        except ImportError:
            logger.warning("RAGAS kütüphanesi bulunamadı, değerlendirme için yükleyin: pip install ragas")
            self.ragas_available = False
    
    def evaluate_answers(
        self, 
        questions: List[str], 
        answers: List[str], 
        contexts: List[List[str]], 
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        RAG sisteminin yanıtlarını değerlendirir.
        
        Args:
            questions: Değerlendirilecek sorular
            answers: RAG sisteminin yanıtları
            contexts: Her soru için kullanılan bağlam chunk'ları
            metrics: Ölçülecek metrikler (varsayılan: tüm metrikler)
            
        Returns:
            Dict[str, Any]: Ölçüm sonuçları
        """
        if not self.ragas_available:
            return {
                "error": "RAGAS kütüphanesi yüklü değil. 'pip install ragas' komutuyla yükleyin."
            }
        
        if not metrics:
            metrics = ["faithfulness", "answer_relevancy", "context_relevancy"]
        
        if len(questions) != len(answers) or len(questions) != len(contexts):
            return {
                "error": f"Eşleşmeyen veri sayısı: {len(questions)} soru, {len(answers)} yanıt, {len(contexts)} bağlam"
            }
        
        try:
            import ragas
            from ragas.langchain.evalchain import RagasEvaluatorChain
            from langchain.schema import Document
            from datasets import Dataset
            
            # Veriyi RAGAS uyumlu formata dönüştür
            data = {
                "question": questions,
                "answer": answers,
                "contexts": [[Document(page_content=c) for c in ctx] for ctx in contexts]
            }
            
            # Dataset oluştur
            dataset = Dataset.from_dict(data)
            
            results = {}
            
            # Seçilen metrikleri değerlendir
            for metric_name in metrics:
                if metric_name in self.metrics:
                    metric = self.metrics[metric_name]
                    evaluator = RagasEvaluatorChain(metric)
                    
                    # Değerlendirme yap
                    metric_result = evaluator.evaluate_dataset(dataset)
                    results[metric_name] = metric_result["score"]
                else:
                    logger.warning(f"Metrik bulunamadı: {metric_name}")
            
            # Toplam puanı hesapla
            if results:
                results["overall_score"] = sum(results.values()) / len(results)
            
            return results
            
        except Exception as e:
            logger.error(f"RAGAS değerlendirme hatası: {str(e)}")
            return {"error": str(e)}
    
    def evaluate_continuous(
        self, 
        query_log_path: str, 
        frequency: str = "daily", 
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sürekli değerlendirme yaparak performans trendini analiz eder.
        
        Args:
            query_log_path: Sorgu günlüğü dosya yolu
            frequency: Değerlendirme sıklığı ("daily", "weekly", "monthly")
            metrics: Ölçülecek metrikler
            
        Returns:
            Dict[str, Any]: Trend analizi sonuçları
        """
        if not self.ragas_available:
            return {
                "error": "RAGAS kütüphanesi yüklü değil. 'pip install ragas' komutuyla yükleyin."
            }
        
        try:
            # Sorgu günlüklerini yükle
            logs = self._load_query_logs(query_log_path)
            
            # Günlükleri zaman periyotlarına ayır
            period_logs = self._group_logs_by_period(logs, frequency)
            
            # Her periyot için değerlendirme yap
            trend_results = {}
            for period, period_data in period_logs.items():
                questions = [entry["query"] for entry in period_data]
                answers = [entry["response"] for entry in period_data]
                contexts = [entry["context_chunks"] for entry in period_data]
                
                # Periyot için değerlendirme yap
                period_results = self.evaluate_answers(questions, answers, contexts, metrics)
                trend_results[period] = period_results
            
            # Trend analizini hesapla
            trends = self._calculate_trends(trend_results)
            
            return {
                "period_scores": trend_results,
                "trends": trends
            }
            
        except Exception as e:
            logger.error(f"Sürekli değerlendirme hatası: {str(e)}")
            return {"error": str(e)}
    
    def evaluate_by_category(
        self, 
        questions: List[str], 
        answers: List[str], 
        contexts: List[List[str]], 
        categories: List[str],
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Kategorilere göre RAG performansını değerlendirir.
        
        Args:
            questions: Değerlendirilecek sorular
            answers: RAG sisteminin yanıtları
            contexts: Her soru için kullanılan bağlam chunk'ları
            categories: Her soru için kategori etiketleri
            metrics: Ölçülecek metrikler
            
        Returns:
            Dict[str, Any]: Kategorilere göre değerlendirme sonuçları
        """
        if not self.ragas_available:
            return {
                "error": "RAGAS kütüphanesi yüklü değil. 'pip install ragas' komutuyla yükleyin."
            }
        
        try:
            # Kategori bazlı gruplama
            category_data = {}
            for q, a, c, cat in zip(questions, answers, contexts, categories):
                if cat not in category_data:
                    category_data[cat] = {
                        "questions": [],
                        "answers": [],
                        "contexts": []
                    }
                
                category_data[cat]["questions"].append(q)
                category_data[cat]["answers"].append(a)
                category_data[cat]["contexts"].append(c)
            
            # Her kategori için değerlendirme yap
            results = {}
            for category, data in category_data.items():
                cat_results = self.evaluate_answers(
                    data["questions"], 
                    data["answers"], 
                    data["contexts"], 
                    metrics
                )
                results[category] = cat_results
            
            # Kategori sonuçlarını karşılaştır
            comparison = self._compare_categories(results)
            
            return {
                "category_scores": results,
                "comparison": comparison
            }
            
        except Exception as e:
            logger.error(f"Kategori değerlendirmesi hatası: {str(e)}")
            return {"error": str(e)}
    
    def benchmark_retrieval(
        self, 
        questions: List[str], 
        ground_truth_docs: List[List[str]], 
        retrieved_docs: List[List[str]]
    ) -> Dict[str, Any]:
        """
        Retrieval performansını altın standart (ground truth) belgelere karşı değerlendirir.
        
        Args:
            questions: Değerlendirilecek sorular
            ground_truth_docs: Her soru için altın standart belgeler
            retrieved_docs: Her soru için gerçekte getirilen belgeler
            
        Returns:
            Dict[str, Any]: Retrieval değerlendirme sonuçları
        """
        try:
            # Precision, Recall ve F1-Score hesapla
            precision_values = []
            recall_values = []
            f1_values = []
            
            for truth_docs, ret_docs in zip(ground_truth_docs, retrieved_docs):
                # Kesişim sayısı (doğru getirilen belgeler)
                true_positives = len(set(truth_docs).intersection(set(ret_docs)))
                
                # Precision: Doğru getirilen / Toplam getirilen
                precision = true_positives / max(len(ret_docs), 1)
                precision_values.append(precision)
                
                # Recall: Doğru getirilen / Toplam olması gereken
                recall = true_positives / max(len(truth_docs), 1)
                recall_values.append(recall)
                
                # F1-Score: Precision ve Recall'un harmonik ortalaması
                if precision + recall > 0:
                    f1 = 2 * (precision * recall) / (precision + recall)
                else:
                    f1 = 0.0
                
                f1_values.append(f1)
            
            # MRR (Mean Reciprocal Rank) hesapla
            mrr_values = []
            
            for truth_docs, ret_docs in zip(ground_truth_docs, retrieved_docs):
                # İlk doğru belgenin sıralamasını bul
                for i, doc in enumerate(ret_docs):
                    if doc in truth_docs:
                        mrr_values.append(1.0 / (i + 1))
                        break
                else:
                    mrr_values.append(0.0)
            
            # Tüm metriklerin ortalamalarını hesapla
            avg_precision = sum(precision_values) / len(precision_values) if precision_values else 0
            avg_recall = sum(recall_values) / len(recall_values) if recall_values else 0
            avg_f1 = sum(f1_values) / len(f1_values) if f1_values else 0
            avg_mrr = sum(mrr_values) / len(mrr_values) if mrr_values else 0
            
            return {
                "precision": avg_precision,
                "recall": avg_recall,
                "f1_score": avg_f1,
                "mrr": avg_mrr,
                "per_question": [
                    {
                        "question": q,
                        "precision": p,
                        "recall": r,
                        "f1_score": f1,
                        "mrr": mrr
                    }
                    for q, p, r, f1, mrr in zip(questions, precision_values, recall_values, f1_values, mrr_values)
                ]
            }
            
        except Exception as e:
            logger.error(f"Retrieval değerlendirme hatası: {str(e)}")
            return {"error": str(e)}
    
    def human_evaluation_template(self, questions: List[str], answers: List[str], contexts: List[List[str]]) -> Dict[str, Any]:
        """
        İnsan değerlendirmesi için şablon oluşturur.
        
        Args:
            questions: Değerlendirilecek sorular
            answers: RAG sisteminin yanıtları
            contexts: Her soru için kullanılan bağlam chunk'ları
            
        Returns:
            Dict[str, Any]: İnsan değerlendirme şablonu
        """
        try:
            template = []
            
            for i, (question, answer, context) in enumerate(zip(questions, answers, contexts)):
                eval_item = {
                    "id": str(i+1),
                    "question": question,
                    "answer": answer,
                    "context": context,
                    "evaluation": {
                        "relevance": {
                            "score": None,  # 1-5 arası puan
                            "comments": ""
                        },
                        "accuracy": {
                            "score": None,  # 1-5 arası puan
                            "comments": ""
                        },
                        "completeness": {
                            "score": None,  # 1-5 arası puan
                            "comments": ""
                        },
                        "context_utilization": {
                            "score": None,  # 1-5 arası puan
                            "comments": ""
                        },
                        "overall": {
                            "score": None,  # 1-5 arası puan
                            "comments": ""
                        }
                    }
                }
                
                template.append(eval_item)
            
            return {
                "instructions": """
                # İnsan Değerlendirme Kılavuzu
                
                Her soru-yanıt çifti için aşağıdaki kriterlere göre 1-5 arası puan verin:
                
                ## Puanlama Kriterleri
                
                - **Alaka Düzeyi (Relevance)**: Yanıt soruyla ne kadar alakalı?
                  - 1: Tamamen alakasız
                  - 5: Mükemmel şekilde alakalı
                
                - **Doğruluk (Accuracy)**: Yanıt ne kadar doğru bilgi içeriyor?
                  - 1: Çoğunlukla yanlış bilgi
                  - 5: Tamamen doğru bilgi
                
                - **Tamlık (Completeness)**: Yanıt soruyu ne kadar tam olarak cevaplıyor?
                  - 1: Soruyu hiç cevaplamıyor
                  - 5: Soruyu tamamen ve eksiksiz cevaplıyor
                
                - **Bağlam Kullanımı (Context Utilization)**: Verilen bağlam ne kadar iyi kullanılmış?
                  - 1: Bağlam hiç kullanılmamış
                  - 5: Bağlam optimal şekilde kullanılmış
                
                - **Genel Değerlendirme (Overall)**: Yanıtın genel kalitesi
                  - 1: Çok kötü
                  - 5: Mükemmel
                """,
                "evaluation_items": template
            }
            
        except Exception as e:
            logger.error(f"İnsan değerlendirme şablonu oluşturma hatası: {str(e)}")
            return {"error": str(e)}
    
    def _load_query_logs(self, log_path: str) -> List[Dict[str, Any]]:
        """Sorgu günlüklerini yükler."""
        with open(log_path, 'r') as f:
            return [json.loads(line) for line in f]
    
    def _group_logs_by_period(self, logs: List[Dict[str, Any]], frequency: str) -> Dict[str, List[Dict[str, Any]]]:
        """Günlükleri zaman periyotlarına göre gruplar."""
        import pandas as pd
        
        # Pandas DataFrame'e dönüştür
        df = pd.DataFrame(logs)
        
        # Zaman sütununu datetime'a dönüştür
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Frekansa göre grupla
        if frequency == 'daily':
            df['period'] = df['timestamp'].dt.strftime('%Y-%m-%d')
        elif frequency == 'weekly':
            df['period'] = df['timestamp'].dt.strftime('%Y-W%U')
        elif frequency == 'monthly':
            df['period'] = df['timestamp'].dt.strftime('%Y-%m')
        else:
            raise ValueError(f"Desteklenmeyen frekans: {frequency}")
        
        # Periyotlara göre grupla
        grouped = df.groupby('period').apply(lambda x: x.to_dict('records')).to_dict()
        
        return grouped
    
    def _calculate_trends(self, period_results: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Zaman içindeki trendleri hesaplar."""
        # Periyotları sırala
        sorted_periods = sorted(period_results.keys())
        
        if len(sorted_periods) <= 1:
            return {"insufficient_data": True}
        
        # Metrik isimlerini al
        metrics = []
        for period, results in period_results.items():
            metrics.extend(results.keys())
        metrics = list(set([m for m in metrics if m != 'overall_score' and not m.startswith('error')]))
        
        # Her metrik için trend hesapla
        trends = {}
        for metric in metrics:
            metric_values = []
            for period in sorted_periods:
                if metric in period_results[period]:
                    metric_values.append(period_results[period][metric])
                else:
                    metric_values.append(None)
            
            # Null değerleri filtrele
            valid_values = [v for v in metric_values if v is not None]
            
            if len(valid_values) <= 1:
                trends[metric] = 0  # Trend yok
                continue
            
            # Son değer ile ilk değer arasındaki değişimi hesapla
            first_valid = valid_values[0]
            last_valid = valid_values[-1]
            
            absolute_change = last_valid - first_valid
            percent_change = (absolute_change / first_valid) * 100 if first_valid != 0 else 0
            
            trends[metric] = {
                "values": metric_values,
                "absolute_change": absolute_change,
                "percent_change": percent_change,
                "direction": "improving" if absolute_change > 0 else "declining" if absolute_change < 0 else "stable"
            }
        
        return trends
    
    def _compare_categories(self, category_results: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Kategori sonuçlarını karşılaştırır ve analiz eder."""
        if not category_results:
            return {}
        
        # Metrik isimlerini al
        metrics = []
        for category, results in category_results.items():
            metrics.extend(results.keys())
        metrics = list(set([m for m in metrics if m != 'overall_score' and not m.startswith('error')]))
        
        # Her metrik için kategoriler arası karşılaştırma
        comparison = {}
        for metric in metrics:
            metric_values = {}
            for category, results in category_results.items():
                if metric in results:
                    metric_values[category] = results[metric]
            
            if not metric_values:
                continue
            
            # En iyi ve en kötü kategorileri bul
            best_category = max(metric_values.items(), key=lambda x: x[1])
            worst_category = min(metric_values.items(), key=lambda x: x[1])
            
            # Ortalamanın üstünde ve altında olan kategorileri bul
            average = sum(metric_values.values()) / len(metric_values)
            above_average = {c: v for c, v in metric_values.items() if v > average}
            below_average = {c: v for c, v in metric_values.items() if v < average}
            
            comparison[metric] = {
                "best": {"category": best_category[0], "score": best_category[1]},
                "worst": {"category": worst_category[0], "score": worst_category[1]},
                "average": average,
                "above_average": above_average,
                "below_average": below_average,
                "range": best_category[1] - worst_category[1]
            }
        
        return comparison
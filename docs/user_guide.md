# ModularMind RAG Platform User Guide

Welcome to the ModularMind RAG Platform user guide. This document will help you get started with using ModularMind for retrieval-augmented generation tasks.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Searching](#searching)
   - [Text Search](#text-search)
   - [Image Search](#image-search)
   - [Audio Search](#audio-search)
3. [Document Management](#document-management)
   - [Uploading Documents](#uploading-documents)
   - [Managing Document Collections](#managing-document-collections)
4. [Analytics](#analytics)
5. [User Management](#user-management)
6. [Settings and Configuration](#settings-and-configuration)

## Getting Started

### Logging In

1. Open your browser and navigate to your ModularMind instance URL.
2. Enter your email address and password.
3. Click "Sign In".

### Dashboard Overview

After logging in, you'll see the main dashboard with:

- Recent search activity
- Document statistics
- Performance metrics
- Quick action buttons

## Searching

ModularMind provides multiple search modalities to find information in your document collection.

### Text Search

For traditional text-based search:

1. Navigate to "Search" in the main menu.
2. Enter your query in the search box.
3. Adjust search options if needed:
   - Search Type: Choose between "Semantic" (default), "Keyword", or "Hybrid".
   - Similarity Threshold: Adjust to control result relevance (0.0-1.0).
   - Result Limit: Number of results to return.
4. Click "Search" to execute your query.
5. Review the results, which include:
   - Relevant text passages
   - Source documents
   - Confidence scores
   - Highlighted key terms

### Image Search

To search using an image:

1. Navigate to "Search" > "Image Search".
2. Upload an image or drag and drop it into the designated area.
3. Optionally add text to refine your search.
4. Click "Search" to find documents related to your image.
5. The system will:
   - Extract visual features from your image
   - Generate a caption automatically
   - Find semantically similar content
   - Return relevant documents and images

### Audio Search

To search using speech or audio:

1. Navigate to "Search" > "Audio Search".
2. Upload an audio file or use the microphone to record.
3. Click "Search" to process the audio.
4. The system will:
   - Transcribe the audio automatically
   - Use the transcript to search for relevant documents
   - Return matched content

## Document Management

### Uploading Documents

To add documents to the system:

1. Navigate to "Upload" in the main menu.
2. Select files from your computer or drag and drop.
3. Supported formats include:
   - PDF (.pdf)
   - Word (.docx, .doc)
   - Text (.txt)
   - Markdown (.md)
   - HTML (.html)
   - Images (.jpg, .png)
4. Configure processing options:
   - **Chunking Strategy**: How documents are split (default: "Semantic")
   - **Chunk Size**: Target size for document chunks (default: 500 tokens)
   - **Chunk Overlap**: Overlap between chunks (default: 50 tokens)
   - **Metadata**: Add custom fields like "category" or "author"
5. Click "Process" to begin document ingestion.
6. Monitor progress on the processing status page.

### Managing Document Collections

To manage your document collections:

1. Navigate to "Documents" in the main menu.
2. View all document collections with statistics.
3. Search or filter by metadata.
4. Select documents to:
   - View details and content
   - Edit metadata
   - Delete or archive
   - Reprocess with different settings

## Analytics

To gain insights into system usage:

1. Navigate to "Analytics" in the main menu.
2. View key metrics:
   - Search volume over time
   - Average response time
   - Most common search terms
   - Document usage statistics
3. Use filters to refine the view by date range or user.
4. Export reports in CSV or PDF format.

## User Management

Available to administrators only:

1. Navigate to "Admin" > "User Management".
2. View all system users.
3. Create new users:
   - Enter name, email, and role
   - System will send invitation email
4. Edit existing users:
   - Change role or status
   - Reset password
5. Define roles with specific permissions.

## Settings and Configuration

To customize your experience:

1. Navigate to "Settings" in the main menu.
2. Adjust personal preferences:
   - Theme (Light/Dark/System)
   - Results per page
   - Default search mode
3. Configure system settings (admin only):
   - API connections
   - Vector database parameters
   - Model selection
   - Embedding configuration
   - Chunking defaults

---

For technical support or questions, please contact your system administrator or submit a support request through the Help menu.
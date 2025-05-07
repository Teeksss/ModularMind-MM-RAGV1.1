"""initial schema

Revision ID: f0d3c6a32e1f
Revises: 
Create Date: 2025-04-29 10:45:21.123456

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'f0d3c6a32e1f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('username', sa.String(), unique=True, nullable=False),
        sa.Column('email', sa.String(), unique=True, nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('role', sa.String(), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key', 'api_keys', ['key'])
    
    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('owner_id', sa.String(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('language', sa.String(), nullable=False, server_default='en'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('enrichment_status', sa.String(), nullable=False, server_default='pending'),
    )
    
    op.create_index('ix_documents_owner_created', 'documents', ['owner_id', sa.text('created_at DESC')])
    op.create_index('ix_documents_language', 'documents', ['language'])
    
    # Document chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('embedding_id', sa.String(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])
    op.create_index('ix_document_chunks_document_index', 'document_chunks', ['document_id', 'chunk_index'])
    
    # Document enrichments table
    op.create_table(
        'document_enrichments',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('agent', sa.String(), nullable=True),
    )
    
    op.create_index('ix_document_enrichments_document_type', 'document_enrichments', ['document_id', 'type'])
    
    # Synthetic QA table
    op.create_table(
        'synthetic_qa',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('source_chunk_id', sa.String(), sa.ForeignKey('document_chunks.id'), nullable=True),
        sa.Column('embedding_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    op.create_index('ix_synthetic_qa_document_id', 'synthetic_qa', ['document_id'])
    
    # Document relations table
    op.create_table(
        'document_relations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('source_id', sa.String(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('target_id', sa.String(), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('concept_name', sa.String(), nullable=True),
        sa.Column('concept_value', sa.String(), nullable=True),
    )
    
    op.create_index('ix_document_relations_source', 'document_relations', ['source_id'])
    op.create_index('ix_document_relations_target', 'document_relations', ['target_id'])
    op.create_index('ix_document_relations_concept', 'document_relations', ['concept_name', 'concept_value'])
    
    # Memory sessions table
    op.create_table(
        'memory_sessions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    
    op.create_index('ix_memory_sessions_user_id', 'memory_sessions', ['user_id'])
    
    # Memory items table
    op.create_table(
        'memory_items',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('session_id', sa.String(), sa.ForeignKey('memory_sessions.id'), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    op.create_index('ix_memory_items_session_id', 'memory_items', ['session_id'])
    op.create_index('ix_memory_items_session_type', 'memory_items', ['session_id', 'type'])
    
    # Queries table
    op.create_table(
        'queries',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', sa.String(), sa.ForeignKey('memory_sessions.id'), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('language', sa.String(), nullable=False, server_default='en'),
        sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_queries_user_id', 'queries', ['user_id'])
    op.create_index('ix_queries_session_id', 'queries', ['session_id'])
    
    # Data sources table
    op.create_table(
        'datasources',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('owner_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    
    op.create_index('ix_datasources_owner_id', 'datasources', ['owner_id'])


def downgrade():
    # Drop tables in reverse order of dependencies
    op.drop_table('datasources')
    op.drop_table('queries')
    op.drop_table('memory_items')
    op.drop_table('memory_sessions')
    op.drop_table('document_relations')
    op.drop_table('synthetic_qa')
    op.drop_table('document_enrichments')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('api_keys')
    op.drop_table('users')
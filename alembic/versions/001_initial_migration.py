"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-05-07 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('organization', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False)
    )
    
    # Create api_tokens table
    op.create_table('api_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True)
    )
    
    # Create document_collections table
    op.create_table('document_collections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('public', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False)
    )
    
    # Create search_logs table
    op.create_table('search_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('search_type', sa.String(50), nullable=False),
        sa.Column('results_count', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    
    # Create indexes
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_api_tokens_user_id'), 'api_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_document_collections_user_id'), 'document_collections', ['user_id'], unique=False)
    op.create_index(op.f('ix_search_logs_user_id'), 'search_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_search_logs_timestamp'), 'search_logs', ['timestamp'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_search_logs_timestamp'), table_name='search_logs')
    op.drop_index(op.f('ix_search_logs_user_id'), table_name='search_logs')
    op.drop_index(op.f('ix_document_collections_user_id'), table_name='document_collections')
    op.drop_index(op.f('ix_api_tokens_user_id'), table_name='api_tokens')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    
    op.drop_table('search_logs')
    op.drop_table('document_collections')
    op.drop_table('api_tokens')
    op.drop_table('users')
"""Create market_analytics table for TickStock Core Universe pressure tracking

Revision ID: create_market_analytics
Revises: [PREVIOUS_REVISION_ID]
Create Date: 2025-06-03 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_market_analytics'
down_revision = None  # Replace with your latest migration ID
branch_labels = None
depends_on = None


def upgrade():
    """Create market_analytics table with indexes and constraints."""
    
    # Create market_analytics table
    op.create_table('market_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_date', sa.Date(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        
        # TickStock Core Universe Pressure - Raw Window Data
        sa.Column('market_net_score', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('market_activity_level', sa.String(length=20), nullable=False),
        sa.Column('market_buying_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('market_selling_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('market_activity_count', sa.Integer(), nullable=False, server_default='0'),
        
        # Rolling Averages for Smooth Visual Display
        sa.Column('avg_net_score_5min', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('avg_net_score_15min', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('avg_net_score_session', sa.Numeric(precision=8, scale=4), nullable=True),
        
        # Enhanced Market Metrics
        sa.Column('buy_events_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sell_events_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unique_buy_tickers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unique_sell_tickers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_universe_size', sa.Integer(), nullable=False, server_default='0'),
        
        # Session Context
        sa.Column('session_total_highs', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('session_total_lows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('session_active_tickers', sa.Integer(), nullable=True, server_default='0'),
        
        # Performance & Metadata
        sa.Column('calc_time_ms', sa.Numeric(precision=8, scale=2), nullable=True, server_default='0'),
        sa.Column('data_source', sa.String(length=50), nullable=True, server_default='live'),
        sa.Column('window_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('window_end_time', sa.DateTime(timezone=True), nullable=True),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Check constraints for data validation
        sa.CheckConstraint('market_net_score BETWEEN -10 AND 10', name='valid_net_score'),
        sa.CheckConstraint("market_activity_level IN ('Low', 'Moderate', 'High', 'Very High')", name='valid_activity_level'),
        sa.CheckConstraint('market_buying_count >= 0', name='valid_buying_count'),
        sa.CheckConstraint('market_selling_count >= 0', name='valid_selling_count'),
        sa.CheckConstraint('market_activity_count >= 0', name='valid_activity_count'),
        sa.CheckConstraint('total_universe_size >= 0', name='valid_universe_size')
    )
    
    # Create indexes for optimal query performance
    
    # Basic indexes for common queries
    op.create_index('idx_market_analytics_session_date', 'market_analytics', ['session_date'])
    op.create_index('idx_market_analytics_timestamp', 'market_analytics', ['timestamp'])
    
    # Composite index for session-based queries
    op.create_index('idx_market_analytics_session_timestamp', 'market_analytics', ['session_date', 'timestamp'])
    
    # Visualization-specific index (session data with smoothed values)
    op.create_index('idx_market_analytics_session_viz', 'market_analytics', 
                   ['session_date', 'timestamp', 'avg_net_score_5min'])
    
    # Real-time dashboard index (most recent data)
    op.create_index('idx_market_analytics_recent_desc', 'market_analytics', 
                   [sa.text('timestamp DESC')])
    
    # Performance monitoring index
    op.create_index('idx_market_analytics_performance', 'market_analytics', 
                   ['session_date', 'data_source', 'calc_time_ms'])
    
    print("✅ Created market_analytics table with all indexes and constraints")


def downgrade():
    """Drop market_analytics table and all associated indexes."""
    
    # Drop indexes first (they'll be dropped automatically with table, but explicit is better)
    index_names = [
        'idx_market_analytics_performance',
        'idx_market_analytics_recent_desc', 
        'idx_market_analytics_session_viz',
        'idx_market_analytics_session_timestamp',
        'idx_market_analytics_timestamp',
        'idx_market_analytics_session_date'
    ]
    
    for index_name in index_names:
        try:
            op.drop_index(index_name, table_name='market_analytics')
        except:
            pass  # Index might not exist, continue
    
    # Drop the table
    op.drop_table('market_analytics')
    
    print("✅ Dropped market_analytics table and all indexes")
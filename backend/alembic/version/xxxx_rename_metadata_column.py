"""fix metadata column name

Revision ID: xxxx
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'xxxx'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Verificar se a coluna 'metadata' existe e renomear
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    if 'metadata' in columns:
        op.alter_column('messages', 'metadata', new_column_name='meta_data')
    elif 'meta_data' not in columns:
        # Se a coluna não existir, criar
        op.add_column('messages', sa.Column('meta_data', sa.JSON(), nullable=True))

def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    if 'meta_data' in columns:
        op.alter_column('messages', 'meta_data', new_column_name='metadata')
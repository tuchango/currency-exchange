"""create db

Revision ID: 6c62ac3c6e51
Revises: 
Create Date: 2024-02-24 20:23:14.409783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c62ac3c6e51'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('currency',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('sign', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_currency_code'), 'currency', ['code'], unique=True)
    op.create_index(op.f('ix_currency_id'), 'currency', ['id'], unique=False)
    op.create_table('exchange_rate',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('base_currency_id', sa.Integer(), nullable=False),
    sa.Column('target_currency_id', sa.Integer(), nullable=False),
    sa.Column('rate', sa.Numeric(), nullable=False),
    sa.ForeignKeyConstraint(['base_currency_id'], ['currency.id'], ),
    sa.ForeignKeyConstraint(['target_currency_id'], ['currency.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('exchange_rate')
    op.drop_index(op.f('ix_currency_id'), table_name='currency')
    op.drop_index(op.f('ix_currency_code'), table_name='currency')
    op.drop_table('currency')
    # ### end Alembic commands ###

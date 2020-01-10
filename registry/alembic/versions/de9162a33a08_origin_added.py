"""origin added

Revision ID: de9162a33a08
Revises: 1d830c8288c7
Create Date: 2020-01-09 14:55:33.959889

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'de9162a33a08'
down_revision = '1d830c8288c7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('organization', sa.Column('origin', sa.VARCHAR(length=128), nullable=True))
    op.add_column('organization_history', sa.Column('origin', sa.VARCHAR(length=128), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('organization_history', 'origin')
    op.drop_column('organization', 'origin')
    # ### end Alembic commands ###

"""empty message

Revision ID: 6628fdc5f40c
Revises: f004a82c083a
Create Date: 2025-05-11 05:16:21.011852

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '6628fdc5f40c'
down_revision = 'f004a82c083a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shared_dataset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('shared_by_id', sa.Integer(), nullable=True))

        batch_op.drop_column('share_date')
        batch_op.drop_column('access_token')

        batch_op.create_foreign_key(
            'fk_shared_dataset_shared_by_id_users',
            'users',
            ['shared_by_id'],
            ['id']
        )


def downgrade():
    op.drop_table('shared_dataset')
    op.create_table(
        'shared_datasets',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('dataset_id', sa.INTEGER(), nullable=False),
        sa.Column('shared_with_id', sa.INTEGER(), nullable=False),
        sa.Column('share_date', sa.DATETIME(), nullable=True),
        sa.Column('access_token', sa.VARCHAR(length=255), nullable=True),
        sa.Column('can_download', sa.BOOLEAN(), nullable=True),
        sa.Column('expires_at', sa.DATETIME(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id']),
        sa.ForeignKeyConstraint(['shared_with_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )


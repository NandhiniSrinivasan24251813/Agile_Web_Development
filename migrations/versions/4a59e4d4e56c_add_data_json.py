"""add data_json

Revision ID: 4a59e4d4e56c
Revises: 9edc99de42ee
Create Date: 2025-05-07 09:48:55.648415

"""
from alembic import op
import sqlalchemy as sa
import json
from datetime import date


# revision identifiers, used by Alembic.
revision = '4a59e4d4e56c'
down_revision = '9edc99de42ee'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('datasets') as batch_op:
        batch_op.add_column(sa.Column('original_filename', sa.String(255),
                                      nullable=True))  
        batch_op.add_column(sa.Column('original_format', sa.String(20),
                                      nullable=True))
        batch_op.add_column(sa.Column('data_json', sa.Text(), nullable=True))

    with op.batch_alter_table('datasets') as batch_op:
        batch_op.alter_column('original_filename',
                              existing_type=sa.String(255),
                              nullable=False)
        batch_op.drop_column('filename')
        # batch_op.drop_column('file_type')
        batch_op.drop_column('filepath')

    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('timezone', sa.String(50)))
        batch_op.add_column(sa.Column('two_factor_enabled', sa.Boolean()))

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('two_factor_enabled')
        batch_op.drop_column('timezone')

    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('filename', sa.VARCHAR(length=255), nullable=False))
        batch_op.add_column(sa.Column('file_type', sa.VARCHAR(length=20), nullable=True))
        batch_op.add_column(sa.Column('filepath', sa.VARCHAR(length=255), nullable=True))
        batch_op.drop_column('data_json')
        batch_op.drop_column('original_format')
        batch_op.drop_column('original_filename')

    # ### end Alembic commands ###

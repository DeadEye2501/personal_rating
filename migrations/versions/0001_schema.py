"""Схема целиком: шестнадцать таблиц каталога и моих данных.

Revision ID: 0001
Revises:
Create Date: 2026-07-29

Тело `upgrade` длиннее предела в сорок строк намеренно: это машинный вывод
автогенерации, сверенный с объявлениями прогоном. Разнести шестнадцать таблиц
по функциям значило бы переписать сгенерированное руками — и получить файл,
который уже не сверить с новым выводом автогенерации.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None


def upgrade() -> None:
    op.create_table('company',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('source_id', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_company')),
    sa.UniqueConstraint('source', 'source_id', name='uq_company_source')
    )
    op.create_table('genre',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_genre')),
    sa.UniqueConstraint('name', 'kind', name='uq_genre_name_kind')
    )
    op.create_table('item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('source_id', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('original_title', sa.Text(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('released_at', sa.Date(), nullable=True),
    sa.Column('synopsis', sa.Text(), nullable=True),
    sa.Column('poster_url', sa.Text(), nullable=True),
    sa.Column('runtime', sa.Integer(), nullable=True),
    sa.Column('seasons_count', sa.Integer(), nullable=True),
    sa.Column('episodes_count', sa.Integer(), nullable=True),
    sa.Column('synced_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_item')),
    sa.UniqueConstraint('kind', 'source', 'source_id', name='uq_item_source')
    )
    op.create_index('ix_item_kind', 'item', ['kind'], unique=False)
    op.create_index('ix_item_kind_year', 'item', ['kind', 'year'], unique=False)
    op.create_table('person',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('source_id', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_person')),
    sa.UniqueConstraint('source', 'source_id', name='uq_person_source')
    )
    op.create_table('tag',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tag')),
    sa.UniqueConstraint('name', 'kind', name='uq_tag_name_kind')
    )
    op.create_table('company_credit',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], name=op.f('fk_company_credit_company_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_company_credit_item_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', 'company_id', 'role', name=op.f('pk_company_credit'))
    )
    op.create_index('ix_company_credit_company_id', 'company_credit', ['company_id'], unique=False)
    op.create_table('external_id',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_external_id_item_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', 'source', name=op.f('pk_external_id')),
    sa.UniqueConstraint('source', 'value', name='uq_external_id_value')
    )
    op.create_table('external_rating',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('value', sa.Float(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_external_rating_item_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', 'source', name=op.f('pk_external_rating'))
    )
    op.create_table('genre_rule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('genre_id', sa.Integer(), nullable=False),
    sa.Column('alone', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['genre_id'], ['genre.id'], name=op.f('fk_genre_rule_genre_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_genre_rule'))
    )
    op.create_index('ix_genre_rule_source', 'genre_rule', ['source'], unique=False)
    op.create_table('genre_rule_mark',
    sa.Column('rule_id', sa.Integer(), nullable=False),
    sa.Column('ext_id', sa.Text(), nullable=False),
    sa.Column('forbidden', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['rule_id'], ['genre_rule.id'], name=op.f('fk_genre_rule_mark_rule_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('rule_id', 'ext_id', name=op.f('pk_genre_rule_mark'))
    )
    op.create_table('item_genre',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('genre_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['genre_id'], ['genre.id'], name=op.f('fk_item_genre_genre_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_item_genre_item_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', 'genre_id', name=op.f('pk_item_genre'))
    )
    op.create_index('ix_item_genre_genre_id', 'item_genre', ['genre_id'], unique=False)
    op.create_table('item_tag',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_item_tag_item_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], name=op.f('fk_item_tag_tag_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', 'tag_id', name=op.f('pk_item_tag'))
    )
    op.create_index('ix_item_tag_tag_id', 'item_tag', ['tag_id'], unique=False)
    op.create_table('person_credit',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_person_credit_item_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], name=op.f('fk_person_credit_person_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', 'person_id', 'role', name=op.f('pk_person_credit'))
    )
    op.create_index('ix_person_credit_person_id', 'person_credit', ['person_id'], unique=False)
    op.create_table('removed',
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('source_id', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('kind', 'source', 'source_id', name=op.f('pk_removed'))
    )
    op.create_table('rating',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('visual', sa.Integer(), nullable=True),
    sa.Column('narrative', sa.Integer(), nullable=True),
    sa.Column('gameplay', sa.Integer(), nullable=True),
    sa.Column('review', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_rating_item_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', name=op.f('pk_rating'))
    )
    op.create_index('ix_rating_score', 'rating', ['score'], unique=False)
    op.create_index('ix_rating_updated_at', 'rating', ['updated_at'], unique=False)
    op.create_table('wishlist',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('added_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], name=op.f('fk_wishlist_item_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', name=op.f('pk_wishlist'))
    )
    op.create_index('ix_wishlist_added_at', 'wishlist', ['added_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_wishlist_added_at', table_name='wishlist')
    op.drop_table('wishlist')
    op.drop_index('ix_rating_updated_at', table_name='rating')
    op.drop_index('ix_rating_score', table_name='rating')
    op.drop_table('rating')
    op.drop_index('ix_person_credit_person_id', table_name='person_credit')
    op.drop_table('person_credit')
    op.drop_index('ix_item_tag_tag_id', table_name='item_tag')
    op.drop_table('item_tag')
    op.drop_index('ix_item_genre_genre_id', table_name='item_genre')
    op.drop_table('item_genre')
    op.drop_table('removed')
    op.drop_table('genre_rule_mark')
    op.drop_index('ix_genre_rule_source', table_name='genre_rule')
    op.drop_table('genre_rule')
    op.drop_table('external_rating')
    op.drop_table('external_id')
    op.drop_index('ix_company_credit_company_id', table_name='company_credit')
    op.drop_table('company_credit')
    op.drop_table('tag')
    op.drop_table('person')
    op.drop_index('ix_item_kind_year', table_name='item')
    op.drop_index('ix_item_kind', table_name='item')
    op.drop_table('item')
    op.drop_table('genre')
    op.drop_table('company')

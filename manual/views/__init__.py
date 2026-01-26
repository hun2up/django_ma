# django_ma/manual/views/__init__.py

"""
manual.views package

- 기존 urls.py / import 경로를 깨지 않기 위해
  이 패키지에서 모든 view callable을 re-export 한다.

예)
- from manual import views
- from manual.views import manual_list
모두 그대로 동작.
"""

from .pages import (
    redirect_to_manual,
    manual_list,
    manual_detail,
    manual_create,
    manual_edit,
    rules_home,
)

from .manual import (
    manual_create_ajax,
    manual_update_title_ajax,
    manual_bulk_update_ajax,
    manual_reorder_ajax,
    manual_delete_ajax,
)

from .section import (
    manual_section_add_ajax,
    manual_section_title_update_ajax,
    manual_section_delete_ajax,
    manual_section_reorder_ajax,
)

from .block import (
    manual_block_add_ajax,
    manual_block_update_ajax,
    manual_block_delete_ajax,
    manual_block_reorder_ajax,
    manual_block_move_ajax,
)

from .attachment import (
    manual_block_attachment_upload_ajax,
    manual_block_attachment_delete_ajax,
)

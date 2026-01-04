# django__ma/partner/migrations/# django__ma/partner/migrations/0019_efficiency_backfill_confirm_group.py

from django.db import migrations

def forwards(apps, schema_editor):
    EfficiencyChange = apps.get_model("partner", "EfficiencyChange")

    # FK 따라가려면 모델 이름 정확히
    EfficiencyConfirmAttachment = apps.get_model("partner", "EfficiencyConfirmAttachment")

    qs = EfficiencyChange.objects.filter(confirm_group__isnull=True).exclude(confirm_attachment__isnull=True)
    for row in qs.iterator():
        att = row.confirm_attachment
        if not att:
            continue
        # att.group가 있어야 정상
        if getattr(att, "group_id", None):
            row.confirm_group_id = att.group_id
            row.save(update_fields=["confirm_group_id"])
        # else: 정책에 따라 스킵/생성 결정

def backwards(apps, schema_editor):
    EfficiencyChange = apps.get_model("partner", "EfficiencyChange")
    # 되돌릴 때 confirm_group만 비우는 정도(선택)
    EfficiencyChange.objects.update(confirm_group=None)

class Migration(migrations.Migration):
    dependencies = [
        ("partner", "0018_efficiency_group_schema"),  # ← 실제 파일명으로 교체
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

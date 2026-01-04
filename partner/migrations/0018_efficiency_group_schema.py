# django_ma/partner/migrations/0018_efficiency_group_schema.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("partner", "0017_remove_efficiencychange_chg_branch_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # ✅ DB에는 "컬럼 추가"를 하지 않는다 (이미 confirm_group_id가 있으므로)
            database_operations=[
                # ✅ (권장) FK 제약조건이 없을 수도 있으니, 있으면 스킵 / 없으면 추가
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'partner_efficiencychange_confirm_group_id_fkey'
                        ) THEN
                            ALTER TABLE partner_efficiencychange
                            ADD CONSTRAINT partner_efficiencychange_confirm_group_id_fkey
                            FOREIGN KEY (confirm_group_id)
                            REFERENCES partner_efficiencyconfirmgroup(id)
                            ON DELETE NO ACTION;
                        END IF;
                    END$$;
                    """,
                    reverse_sql="""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'partner_efficiencychange_confirm_group_id_fkey'
                        ) THEN
                            ALTER TABLE partner_efficiencychange
                            DROP CONSTRAINT partner_efficiencychange_confirm_group_id_fkey;
                        END IF;
                    END$$;
                    """,
                ),
            ],
            # ✅ Django state에는 "confirm_group 필드가 존재한다"를 반영
            state_operations=[
                migrations.AddField(
                    model_name="efficiencychange",
                    name="confirm_group",
                    field=models.ForeignKey(
                        to="partner.efficiencyconfirmgroup",
                        on_delete=django.db.models.deletion.SET_NULL,  # 0020에서 PROTECT로 바뀜
                        related_name="efficiency_rows",
                        null=True,
                        blank=True,
                        verbose_name="확인서 그룹",
                    ),
                ),
            ],
        ),
    ]

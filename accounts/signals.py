# django_ma/accounts/signals.py
from __future__ import annotations

from django.apps import apps
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import CustomUser


def _to_str(v) -> str:
    return ("" if v is None else str(v)).strip()


def _get_subadmin_model():
    # partner.models.SubAdminTemp를 지연 로딩하여 순환 import 방지
    return apps.get_model("partner", "SubAdminTemp")


@receiver(pre_save, sender=CustomUser)
def _capture_old_grade(sender, instance: CustomUser, **kwargs):
    """
    저장 직전 DB의 기존 grade를 instance에 임시 저장.
    - admin에서 grade를 변경해 저장해도 '변경 전/후' 감지 가능
    """
    if not instance.pk:
        instance._old_grade = ""
        return

    try:
        old = sender.objects.filter(pk=instance.pk).values_list("grade", flat=True).first()
    except Exception:
        old = ""

    instance._old_grade = _to_str(old)


@receiver(post_save, sender=CustomUser)
def _sync_subadmin_on_grade_change(sender, instance: CustomUser, created: bool, **kwargs):
    """
    ✅ grade가 leader로 바뀐 경우(SubAdminTemp 자동 생성/최소 갱신)
    - team_a/b/c, position은 덮어쓰기 금지
    - 없으면 생성(최소 필드)
    - 있으면 name/part/branch/grade만 최신화
    """
    SubAdminTemp = _get_subadmin_model()

    new_grade = _to_str(instance.grade)
    old_grade = _to_str(getattr(instance, "_old_grade", ""))

    # created=True 신규 생성인 경우: "승격/강등" 판단을 old_grade로 하지 말고
    # 현재 grade만 보고 최소 보장
    if created:
        if new_grade == "leader":
            SubAdminTemp.objects.get_or_create(
                user=instance,
                defaults={
                    "name": _to_str(instance.name) or "-",
                    "branch": _to_str(instance.branch) or "-",
                    "part": _to_str(instance.part) or "-",
                    "grade": "leader",
                    "level": "-",
                },
            )
        return

    became_leader = (new_grade == "leader") and (old_grade != "leader")
    left_leader = (old_grade == "leader") and (new_grade != "leader")

    # 1) leader로 승격된 경우: SubAdminTemp 보장
    if became_leader:
        sa, sa_created = SubAdminTemp.objects.get_or_create(
            user=instance,
            defaults={
                # 최소 필드만: 팀/직급은 건드리지 않음(NULL 유지)
                "name": _to_str(instance.name) or "-",
                "branch": _to_str(instance.branch) or "-",
                "part": _to_str(instance.part) or "-",
                "grade": "leader",
                "level": "-",
            },
        )

        # 이미 존재하면 team/position은 그대로 두고 메타만 최신화
        updates = {}
        if _to_str(getattr(sa, "name", "")) != (_to_str(instance.name) or "-"):
            updates["name"] = _to_str(instance.name) or "-"
        if _to_str(getattr(sa, "branch", "")) != (_to_str(instance.branch) or "-"):
            updates["branch"] = _to_str(instance.branch) or "-"
        if _to_str(getattr(sa, "part", "")) != (_to_str(instance.part) or "-"):
            updates["part"] = _to_str(instance.part) or "-"
        if _to_str(getattr(sa, "grade", "")) != "leader":
            updates["grade"] = "leader"
        if _to_str(getattr(sa, "level", "")) == "":
            updates["level"] = "-"

        if updates and not sa_created:
            SubAdminTemp.objects.filter(pk=sa.pk).update(**updates)

        return

    # 2) leader에서 내려간 경우: 삭제 금지 + 팀/직급 유지, grade/level만 최소 동기화
    if left_leader:
        qs = SubAdminTemp.objects.filter(user=instance)
        if qs.exists():
            qs.update(
                grade=new_grade or "basic",
                level="-",
                name=_to_str(instance.name) or "-",
                branch=_to_str(instance.branch) or "-",
                part=_to_str(instance.part) or "-",
            )

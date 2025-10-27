from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from accounts.models import CustomUser
from .models import SubAdminTemp


@receiver(post_save, sender=CustomUser)
def sync_subadmin_from_user(sender, instance, created, **kwargs):
    """
    ✅ CustomUser가 생성·수정될 때 SubAdminTemp 자동 동기화
    - grade == 'sub_admin' → 생성 또는 업데이트
    - grade != 'sub_admin' → SubAdminTemp에서 제거
    - 부서/지점/성명/사번/등급은 CustomUser 기준으로 갱신
    - 팀A/B/C/직급/레벨은 SubAdminTemp 기존값 유지
    """
    try:
        # 1️⃣ sub_admin이 아닌 경우 → SubAdminTemp에서 제거
        if instance.grade != "sub_admin":
            SubAdminTemp.objects.filter(user=instance).delete()
            return

        # 2️⃣ sub_admin인 경우 → CustomUser 정보로 갱신 or 생성
        existing = SubAdminTemp.objects.filter(user=instance).first()

        if existing:
            # ✅ 기존 데이터 유지하며 CustomUser 필드만 갱신
            existing.branch = instance.branch or existing.branch
            existing.part = instance.part or existing.part
            existing.name = instance.name or existing.name
            existing.save(update_fields=["branch", "part", "name"])
        else:
            # ✅ 신규 생성 (팀/직급/레벨은 기본값으로)
            SubAdminTemp.objects.create(
                user=instance,
                name=instance.name,
                branch=instance.branch,
                part=instance.part,
                position="-",
                team_a="-",
                team_b="-",
                team_c="-",
                level="-",
            )

    except Exception as e:
        print(f"[SubAdmin Sync Error] {e}")


@receiver(pre_delete, sender=CustomUser)
def remove_subadmin_when_user_deleted(sender, instance, **kwargs):
    """✅ CustomUser 삭제 시 SubAdminTemp에서도 삭제"""
    try:
        SubAdminTemp.objects.filter(user=instance).delete()
    except Exception as e:
        print(f"[SubAdmin Delete Sync Error] {e}")

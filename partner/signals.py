# django_ma/partner/signals.py
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
    """
    try:
        # 중간관리자가 아닌 경우 → 기존 데이터 삭제
        if instance.grade != "sub_admin":
            SubAdminTemp.objects.filter(user=instance).delete()
            return

        # 중간관리자인 경우 → 생성 또는 업데이트
        SubAdminTemp.objects.update_or_create(
            user=instance,
            defaults={
                "branch": instance.branch,
                "part": instance.part,
                "position": getattr(instance, "grade", "") or "",
                "level": getattr(instance, "level", "-") if hasattr(instance, "level") else "-",
            },
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

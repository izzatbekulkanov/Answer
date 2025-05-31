from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=100, verbose_name=_("Ism"))
    last_name = models.CharField(max_length=100, verbose_name=_("Familiya"))
    patronymic = models.CharField(max_length=100, blank=True, verbose_name=_("Otasining ismi"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("Tug'ilgan yil"))
    profile_picture = models.ImageField(upload_to='profile_pics/%Y/%m/%d/', null=True, blank=True, verbose_name=_("Profil rasmi"))
    phone_number = models.CharField(max_length=20, blank=True, verbose_name=_("Telefon raqami"))
    address = models.TextField(blank=True, verbose_name=_("Manzil"))
    personal_code = models.CharField(max_length=50, blank=True, unique=True, verbose_name=_("Shaxsiy parol"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan sana"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan sana"))

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class UserUsage(models.Model):
    """
    Foydalanuvchining Chrome extension’dan foydalanish statistikasini saqlash uchun model.
    Har bir foydalanuvchi necha marta “Boshlash” tugmasini bosganini va oxirgi foydalanish vaqtini hisoblaydi.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="usages",
        verbose_name=_("Foydalanuvchi"),
        help_text=_("Ushbu faoliyat qaysi foydalanuvchiga tegishli ekanligini ko‘rsatadi.")
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Foydalanish soni"),
        help_text=_("Foydalanuvchi extension’dan necha marta foydalanganini ko‘rsatadi.")
    )
    last_used = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Oxirgi foydalanish"),
        help_text=_("Foydalanuvchi oxirgi marta extension’dan foydalangan vaqt, har safar yangilanadi.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Yaratilgan sana"),
        help_text=_("Foydalanish yozuvi yaratilgan vaqt, avtomatik to‘ldiriladi.")
    )

    class Meta:
        verbose_name = _("Foydalanuvchi faoliyati")
        verbose_name_plural = _("Foydalanuvchi faoliyatlari")
        # Modelning admin paneldagi nomi va ko‘plik shakli.

    def __str__(self):
        """
        Foydalanuvchi va uning foydalanish sonini qaytaradi.
        Admin panelda yoki loglarda yozuvni aniqlash uchun ishlatiladi.
        """
        return f"{self.user}: {self.usage_count} marta"

class Question(models.Model):
    text = models.CharField(max_length=1000, verbose_name=_("Savol matni"))
    clean_text = models.CharField(max_length=1000, blank=True, verbose_name=_("Tozalangan savol matni"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan sana"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan sana"))
    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions', verbose_name=_("Qo‘shgan foydalanuvchi"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))

    class Meta:
        verbose_name = _("Savol")
        verbose_name_plural = _("Savollar")

    def save(self, *args, **kwargs):
        from .views import clean_text  # Circular importdan qochish
        self.clean_text = clean_text(self.text)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', verbose_name=_("Savol"))
    text = models.CharField(max_length=1000, verbose_name=_("Javob matni"))
    clean_text = models.CharField(max_length=1000, blank=True, verbose_name=_("Tozalangan javob matni"))
    is_correct = models.BooleanField(default=False, verbose_name=_("To‘g‘ri javob"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan sana"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan sana"))
    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='answers', verbose_name=_("Qo‘shgan foydalanuvchi"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))

    class Meta:
        verbose_name = _("Javob")
        verbose_name_plural = _("Javoblar")

    def save(self, *args, **kwargs):
        from .views import clean_text
        self.clean_text = clean_text(self.text)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text
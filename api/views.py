from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from quiz_app.models import Question, CustomUser, UserUsage
from quiz_app.views import clean_text, clean_json_string
from fuzzywuzzy import fuzz
from django.db.models import F


@csrf_exempt
def verify_pin(request):
    print("🔍 Kiruvchi so‘rov: PIN tekshiruvi")

    if request.method != 'POST':
        print("❌ Notog‘ri so‘rov turi!")
        return JsonResponse({
            "success": False,
            "message": "Faqat POST so‘rovi qabul qilinadi!"
        }, status=405)

    try:
        pin = request.POST.get('pin', '').strip()
        print("📝 Kiritilgan PIN:", pin)

        if len(pin) != 4 or not pin.isdigit():
            print("⚠️ Noto‘g‘ri PIN formati!")
            return JsonResponse({
                "success": False,
                "message": "PIN 4 raqamdan iborat bo‘lishi kerak!"
            }, status=400)

        user = CustomUser.objects.filter(personal_code=pin, is_active=True).first()
        print("📦 Topilgan foydalanuvchi:", user)

        if not user:
            print("❌ PIN mos foydalanuvchi topilmadi.")
            return JsonResponse({
                "success": False,
                "message": "Noto‘g‘ri PIN!"
            }, status=404)

        return JsonResponse({
            "success": True,
            "user_id": user.id,
            "full_name": f"{user.first_name} {user.last_name}"
        }, status=200)

    except Exception as e:
        print(f"🔥 Xatolik yuz berdi: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"Xatolik: {str(e)}"
        }, status=500)


@csrf_exempt
def track_usage(request):
    print("🔍 Kiruvchi so‘rov: Foydalanishni hisoblash")

    if request.method != 'POST':
        print("❌ Notog‘ri so‘rov turi!")
        return JsonResponse({
            "success": False,
            "message": "Faqat POST so‘rovi qabul qilinadi!"
        }, status=405)

    try:
        user_id = request.POST.get('user_id')
        print("📝 Foydalanuvchi ID:", user_id)

        if not user_id:
            print("⚠️ Foydalanuvchi ID kiritilmadi.")
            return JsonResponse({
                "success": False,
                "message": "Foydalanuvchi ID talab qilinadi!"
            }, status=400)

        user = CustomUser.objects.filter(id=user_id, is_active=True).first()
        if not user:
            print("❌ Foydalanuvchi topilmadi.")
            return JsonResponse({
                "success": False,
                "message": "Foydalanuvchi topilmadi!"
            }, status=404)

        usage, created = UserUsage.objects.get_or_create(user=user, defaults={"usage_count": 0})
        usage.usage_count = F('usage_count') + 1
        usage.save()
        usage.refresh_from_db()
        print(f"✅ Foydalanish hisoblandi: {usage.usage_count} marta")

        return JsonResponse({
            "success": True,
            "usage_count": usage.usage_count
        }, status=200)

    except Exception as e:
        print(f"🔥 Xatolik yuz berdi: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"Xatolik: {str(e)}"
        }, status=500)


def search_question(request):
    print("🔍 Kiruvchi so‘rov:", request.method)

    if request.method != 'GET':
        print("❌ Notog‘ri so‘rov turi!")
        return JsonResponse({
            "success": False,
            "message": "Faqat GET so‘rovi qabul qilinadi!"
        }, status=405)

    query = request.GET.get('q', '').strip()
    print("📝 Foydalanuvchi so‘rovi:", query)

    if not query:
        print("⚠️ Bo‘sh so‘rov kiritildi.")
        return JsonResponse({
            "success": False,
            "message": "Savol matni kiritilmadi!"
        }, status=400)

    try:
        clean_query = clean_text(query)
        print("🧹 Tozalangan so‘rov:", clean_query)

        if not clean_query:
            print("❌ Tozalangan matn yaroqsiz.")
            return JsonResponse({
                "success": False,
                "message": "Yaroqli savol matni kiritilmadi!"
            }, status=400)

        questions = Question.objects.filter(is_active=True)
        print(f"📚 Faol savollar soni: {questions.count()}")

        if not questions.exists():
            print("❌ Hech qanday faol savol topilmadi.")
            return JsonResponse({
                "success": False,
                "message": "Savol topilmadi!"
            }, status=404)

        best_match = max(
            questions,
            key=lambda q: fuzz.partial_ratio(clean_query, q.clean_text),
            default=None
        )
        similarity_score = fuzz.partial_ratio(clean_query, best_match.clean_text) if best_match else 0
        print(f"🔎 Eng yaqin savol: {best_match.text if best_match else 'None'}, O‘xshashlik: {similarity_score}%")

        if not best_match or similarity_score < 80:
            print("❌ Mos savol topilmadi (o‘xshashlik 80% dan past).")
            return JsonResponse({
                "success": False,
                "message": "Savol topilmadi!"
            }, status=404)

        correct_answer = best_match.answers.filter(
            is_correct=True,
            is_active=True
        ).first()
        print("✅ Topilgan to‘g‘ri javob:", correct_answer.text if correct_answer else "Yo‘q")

        if not correct_answer:
            print("❌ To‘g‘ri javob topilmadi.")
            return JsonResponse({
                "success": False,
                "message": "To‘g‘ri javob topilmadi!"
            }, status=404)

        response = {
            "success": True,
            "question": clean_json_string(best_match.text),
            "correct_answer": {
                "text": clean_json_string(correct_answer.text),
                "clean_text": clean_json_string(correct_answer.clean_text)
            },
            "similarity_score": similarity_score
        }
        print("📤 Javob JSON:", response)
        return JsonResponse(response, status=200)

    except Exception as e:
        print(f"🔥 Xatolik yuz berdi: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"Xatolik: {str(e)}"
        }, status=500)

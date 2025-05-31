import re
import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import generics
from .models import Question, Answer, CustomUser
from .serializers import QuestionSerializer

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
class QuestionListView(generics.ListAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


@transaction.atomic
def clean_duplicate_questions():
    duplicate_questions = Question.objects.values('clean_text').annotate(count=Count('id')).filter(count__gt=1)
    cleaned_count = 0
    for duplicate in duplicate_questions:
        question_text = duplicate['clean_text']
        questions = Question.objects.filter(clean_text=question_text).order_by('id')
        first_question = questions.first()
        for question in questions[1:]:
            answers = Answer.objects.filter(question=question)
            for answer in answers:
                if not Answer.objects.filter(question=first_question, clean_text=answer.clean_text,
                                             is_correct=answer.is_correct).exists():
                    Answer.objects.create(
                        question=first_question,
                        text=answer.text,
                        clean_text=answer.clean_text,
                        is_correct=answer.is_correct,
                        added_by=answer.added_by
                    )
            question.delete()
            cleaned_count += 1
    return {
        'status': 'success',
        'message': f'{cleaned_count} ta takrorlanadigan savol tozalandi.'
    }


@csrf_exempt
def clean_duplicates_view(request):
    if request.method == 'POST':
        try:
            result = clean_duplicate_questions()
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Faqat POST so‘roviga ruxsat!'}, status=405)


def clean_json_string(text):
    """Escape special characters to make text JSON-safe."""
    if not text:
        return text
    # Replace control characters and ensure proper escaping
    text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    text = text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
    return text

@login_required
def index(request):
    search_query = request.GET.get('q', '').strip()
    clean_query = clean_text(search_query) if search_query else ''

    questions = Question.objects.filter(is_active=True).prefetch_related('answers')
    if clean_query:
        questions = questions.filter(clean_text__contains=clean_query)

    questions_data = [
        {
            'id': q.id,
            'text': clean_json_string(q.text),
            'clean_text': q.clean_text,
            'created_at': q.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'added_by': clean_json_string(q.added_by.username) if q.added_by else 'Noma’lum',
            'is_active': q.is_active,
            'answers': [
                {
                    'text': clean_json_string(a.text),
                    'clean_text': a.clean_text,
                    'is_correct': a.is_correct,
                    'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                for a in q.answers.filter(is_active=True)
            ]
        }
        for q in questions
    ]

    context = {
        'questions_json': json.dumps(questions_data, ensure_ascii=False, sort_keys=True),
        'search_query': search_query,
        'total_questions': questions.count(),
        'error': 'Savollar topilmadi!' if not questions.exists() and search_query else None
    }

    return render(request, 'index.html', context)


def questions(request):
    questions = Question.objects.filter(is_active=True).prefetch_related('answers')
    return render(request, 'questions.html', {'questions': questions})


def clean_text(text):
    """Matnni tozalash: maxsus belgilarni olib tashlaydi, kichik harfga aylantiradi va ortiqcha bo‘shliqlarni olib tashlaydi."""
    if not text:
        return ""
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lower()
    text = text.replace("’", "").replace("'", "")
    return text

def hemis_upload(request):
    if request.method == 'POST':
        file = request.FILES.get('hemis_file')
        if file and file.name.endswith('.txt'):
            try:
                if file.size > 5 * 1024 * 1024:
                    return JsonResponse({'status': 'error', 'message': 'Fayl hajmi 5MB dan katta!'}, status=400)
                content = file.read().decode('utf-8')
                questions = []
                blocks = content.split('+++++')
                for idx, block in enumerate(blocks, 1):
                    block = block.strip()
                    if not block:
                        continue
                    parts = re.split(r'\n=+\s*\n', block)
                    if len(parts) < 2:
                        continue
                    question_text = parts[0].strip()
                    clean_question = clean_text(question_text)
                    if not clean_question:
                        continue
                    answers = []
                    for answer_text in parts[1:]:
                        answer_text = answer_text.strip()
                        if not answer_text:
                            continue
                        is_correct = answer_text.startswith('#')
                        answer_text = answer_text.lstrip('#').strip()
                        clean_answer = clean_text(answer_text)
                        if clean_answer:
                            answers.append({
                                'text': answer_text.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r'),
                                'clean_text': clean_answer,
                                'is_correct': is_correct
                            })
                    if answers:
                        questions.append({
                            'number': idx,
                            'text': question_text.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r'),
                            'clean_text': clean_question,
                            'answers': answers,
                            'correctAnswers': [a for a in answers if a['is_correct']]
                        })
                if not questions:
                    return JsonResponse({'status': 'error', 'message': 'Faylda savollar topilmadi!'}, status=400)
                # Sessiyaga saqlash (agar kerak bo‘lsa)
                request.session['parsed_questions'] = json.dumps(questions, ensure_ascii=False)
                # AJAX uchun JSON javob
                return JsonResponse({'status': 'success', 'questions': questions})
            except UnicodeDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Fayl UTF-8 formatida bo‘lishi kerak!'}, status=400)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Xato: {str(e)}'}, status=400)
        return JsonResponse({'status': 'error', 'message': 'Faqat .txt fayl!'}, status=400)
    parsed_questions = request.session.get('parsed_questions', '[]')
    return render(request, 'questions.html', {'parsed_questions': parsed_questions})

@login_required
@require_POST
def hemis_save(request):
    try:
        questions_json = request.POST.get('questions')
        if not questions_json:
            return JsonResponse({'status': 'error', 'message': 'Savollar topilmadi!'}, status=400)

        questions = json.loads(questions_json)
        created_questions = []

        for q in questions:
            clean_question = clean_text(q['text'])
            if not clean_question:
                continue

            question, created = Question.objects.get_or_create(
                clean_text=clean_question,
                defaults={
                    'text': q['text'],
                    'added_by': request.user,
                    'is_active': True
                }
            )

            answers_to_create = []
            for answer in q.get('answers', []):
                clean_answer = clean_text(answer['text'])
                if not clean_answer:
                    continue

                if not Answer.objects.filter(
                        question=question,
                        clean_text=clean_answer,
                        is_correct=answer.get('is_correct', False)
                ).exists():
                    answers_to_create.append(Answer(
                        question=question,
                        text=answer['text'],
                        clean_text=clean_answer,
                        is_correct=answer.get('is_correct', False),
                        added_by=request.user,
                        is_active=True
                    ))

            if answers_to_create:
                Answer.objects.bulk_create(answers_to_create)
                created_questions.append({
                    'text': q['text'],
                    'answers': [a.text for a in answers_to_create]
                })

        if not created_questions:
            return JsonResponse({'status': 'error', 'message': 'Yangi savollar topilmadi yoki barchasi mavjud!'}, status=400)

        # Sessiyani tozalash
        if 'parsed_questions' in request.session:
            del request.session['parsed_questions']

        return JsonResponse({
            'status': 'success',
            'message': f'{len(created_questions)} ta savol muvaffaqiyatli saqlandi!'
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON formatida xatolik!'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def users_list(request):
    users = CustomUser.objects.all().values(
        'id', 'username', 'first_name', 'last_name', 'personal_code', 'created_at', 'is_active'
    )
    users_json = json.dumps(list(users), default=str)
    return render(request, 'users.html', {'users_json': users_json})


def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        patronymic = request.POST.get('patronymic', '')
        birth_date = request.POST.get('birth_date')
        phone_number = request.POST.get('phone_number', '')
        address = request.POST.get('address', '')
        personal_code_1 = request.POST.get('personal_code_1', '')
        personal_code_2 = request.POST.get('personal_code_2', '')
        personal_code_3 = request.POST.get('personal_code_3', '')
        personal_code_4 = request.POST.get('personal_code_4', '')
        profile_picture = request.FILES.get('profile_picture')

        personal_code = personal_code_1 + personal_code_2 + personal_code_3 + personal_code_4

        if not all([username, first_name, last_name]):
            return render(request, 'add_user.html', {'error': 'Majburiy maydonlar to‘ldirilmadi!'})
        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'add_user.html', {'error': 'Bunday username mavjud!'})
        if personal_code:
            if not (personal_code.isdigit() and len(personal_code) == 4):
                return render(request, 'add_user.html', {'error': 'Shaxsiy kod 4 raqamli bo‘lishi kerak!'})
            if CustomUser.objects.filter(personal_code=personal_code).exists():
                return render(request, 'add_user.html', {'error': 'Bunday shaxsiy kod mavjud!'})

        user = CustomUser(
            username=username,
            first_name=first_name,
            last_name=last_name,
            patronymic=patronymic,
            birth_date=birth_date or None,
            phone_number=phone_number,
            address=address,
            personal_code=personal_code,
            password=make_password('admin1231'),
            is_active=True,
            is_staff=True
        )
        if profile_picture:
            user.profile_picture = profile_picture
        user.save()
        return redirect('users')
    return render(request, 'add_user.html')


@csrf_exempt
def check_username(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        if not username:
            return JsonResponse({'status': 'error', 'message': 'Username bo‘sh bo‘lmasligi kerak!'})
        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Bunday username mavjud!'})
        return JsonResponse({'status': 'success', 'message': 'Username mavjud emas, ishlatish mumkin!'})
    return JsonResponse({'status': 'error', 'message': 'Faqat POST so‘rovlar qabul qilinadi'})


@csrf_exempt
def check_personal_code(request):
    if request.method == 'POST':
        personal_code = request.POST.get('personal_code', '').strip()
        user_id = request.POST.get('user_id', None)
        if not personal_code:
            return JsonResponse({'status': 'error', 'message': 'Shaxsiy kod bo‘sh bo‘lmasligi kerak!'})
        if not (personal_code.isdigit() and len(personal_code) == 4):
            return JsonResponse({'status': 'error', 'message': 'Shaxsiy kod 4 raqamli bo‘lishi kerak!'})
        if CustomUser.objects.filter(personal_code=personal_code).exclude(id=user_id).exists():
            return JsonResponse({'status': 'error', 'message': 'Bunday shaxsiy kod mavjud!'})
        return JsonResponse({'status': 'success', 'message': 'Shaxsiy kod mavjud emas, ishlatish mumkin!'})
    return JsonResponse({'status': 'error', 'message': 'Faqat POST so‘rovlar qabul qilinadi'})


@csrf_exempt
def delete_user(request, user_id):
    if request.method == 'DELETE':
        try:
            user = CustomUser.objects.get(id=user_id)
            user.delete()
            return JsonResponse({'status': 'success', 'message': 'Foydalanuvchi o‘chirildi!'})
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Foydalanuvchi topilmadi!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Faqat DELETE so‘rovlar qabul qilinadi'})


@csrf_exempt
def reset_password(request, user_id):
    if request.method == 'POST':
        try:
            user = CustomUser.objects.get(id=user_id)
            user.password = make_password('admin1231')
            user.save()
            return JsonResponse({'status': 'success', 'message': 'Parol tiklandi!'})
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Foydalanuvchi topilmadi!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Faqat POST so‘rovlar qabul qilinadi'})


def clean_input(value):
    if not value:
        return value
    cleaned = re.sub(r'[\'\\"]+', '', value)
    return cleaned.strip()


@user_passes_test(lambda u: u.is_superuser)
def user_detail(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        if request.method == 'POST':
            username = clean_input(request.POST.get('username'))
            first_name = clean_input(request.POST.get('first_name'))
            last_name = clean_input(request.POST.get('last_name'))
            patronymic = clean_input(request.POST.get('patronymic', ''))
            birth_date = request.POST.get('birth_date')
            phone_number = clean_input(request.POST.get('phone_number', ''))
            address = clean_input(request.POST.get('address', ''))
            personal_code_1 = request.POST.get('personal_code_1', '')
            personal_code_2 = request.POST.get('personal_code_2', '')
            personal_code_3 = request.POST.get('personal_code_3', '')
            personal_code_4 = request.POST.get('personal_code_4', '')
            profile_picture = request.FILES.get('profile_picture')
            is_active = request.POST.get('is_active') == 'on'

            personal_code = personal_code_1 + personal_code_2 + personal_code_3 + personal_code_4

            if not all([username, first_name, last_name]):
                return render(request, 'user_detail.html', {'user': user, 'error': 'Majburiy maydonlar to‘ldirilmadi!'})
            if CustomUser.objects.filter(username=username).exclude(id=user_id).exists():
                return render(request, 'user_detail.html', {'user': user, 'error': 'Bunday username mavjud!'})
            if personal_code:
                if not (personal_code.isdigit() and len(personal_code) == 4):
                    return render(request, 'user_detail.html',
                                  {'user': user, 'error': 'Shaxsiy kod 4 raqamli bo‘lishi kerak!'})
                if CustomUser.objects.filter(personal_code=personal_code).exclude(id=user_id).exists():
                    return render(request, 'user_detail.html', {'user': user, 'error': 'Bunday shaxsiy kod mavjud!'})

            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.patronymic = patronymic
            user.birth_date = birth_date or None
            user.phone_number = phone_number
            user.address = address
            user.personal_code = personal_code
            user.is_active = is_active
            if profile_picture:
                user.profile_picture = profile_picture
            user.save()
            return redirect('user_detail', user_id=user_id)

        return render(request, 'user_detail.html', {'user': user})
    except CustomUser.DoesNotExist:
        return render(request, 'user_detail.html', {'error': 'Foydalanuvchi topilmadi!'})


def search_question(request):
    if request.method == 'GET':
        query = request.GET.get('q', '')
        if not query:
            return JsonResponse({"success": False, "message": "Savol kiritilmadi!"})

        clean_query = clean_text(query)

        try:
            question = Question.objects.filter(clean_text__contains=clean_query, is_active=True).first()
            if not question:
                return JsonResponse({"success": False, "message": "Savol topilmadi!"})

            correct_answer = question.answers.filter(is_correct=True, is_active=True).first()
            if not correct_answer:
                return JsonResponse({"success": False, "message": "To‘g‘ri javob topilmadi!"})

            return JsonResponse({
                "success": True,
                "question": question.text,
                "correct_answer": correct_answer.text
            })
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Xatolik: {str(e)}"})

    return JsonResponse({"success": False, "message": "Faqat GET so‘rovi qabul qilinadi!"})

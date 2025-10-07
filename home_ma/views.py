from django.http import HttpResponse

def home(request):
    return HttpResponse("인카금융서비스 MA부문 업무지원 홈페이지 입니다.")
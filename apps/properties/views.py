from django.http import JsonResponse

from .geography import geography_payload


def geography_data(request):
    return JsonResponse(geography_payload())

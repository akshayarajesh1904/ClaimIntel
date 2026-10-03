from .models import Policy


def policy_status(request):

    if request.user.is_authenticated:
        return {
            'has_policy': Policy.objects.filter(
                policyholder=request.user
            ).exists()
        }

    return {
        'has_policy': False
    }
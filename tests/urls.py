from django.urls import path

from django_altcha_widget import AltchaChallengeView

urlpatterns = [
    path(
        "altcha/challenge/",
        AltchaChallengeView.as_view(cost=100),
        name="altcha_challenge",
    ),
    path(
        "altcha/challenge/defaults/",
        AltchaChallengeView.as_view(),
        name="altcha_challenge_defaults",
    ),
]

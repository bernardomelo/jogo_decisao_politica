from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    # Jogo principal
    path('', views.game_view, name='game'),
]
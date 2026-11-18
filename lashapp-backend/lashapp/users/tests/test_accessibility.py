from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AccessibilityPreferencesAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="acessibilidade@example.com",
            password="senha-forte-123",
            name="Usuario Acessivel",
        )
        self.url = "/api/users/me/accessibility/"

    def test_le_valores_padrao(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"high_contrast": False, "font_scale": 100})

    def test_atualizacao_valida(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"high_contrast": True, "font_scale": 150},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.high_contrast)
        self.assertEqual(self.user.font_scale, 150)

    def test_rejeita_font_scale_abaixo_do_intervalo(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"font_scale": 99},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("font_scale", response.data)

    def test_rejeita_font_scale_acima_do_intervalo(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"font_scale": 151},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("font_scale", response.data)

    def test_acesso_sem_autenticacao_negado(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

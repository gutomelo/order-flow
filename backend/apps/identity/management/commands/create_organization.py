"""Onboarding de organização pelo operador da plataforma (docs/domain/identity.md)."""

import getpass
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils.text import slugify

from apps.identity.domain.permissions import Role
from apps.identity.models import Organization, User, normalize_email


class Command(BaseCommand):
    help = "Cria uma organização (tenant) e o seu primeiro ADMIN."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--name", required=True, help="Nome da organização")
        parser.add_argument("--slug", help="Identificador único (padrão: derivado do nome)")
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--admin-first-name", default="Admin")
        parser.add_argument(
            "--admin-password",
            help="Senha do ADMIN. Se omitida, é solicitada no terminal (recomendado).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        slug = options["slug"] or slugify(options["name"])
        email = normalize_email(options["admin_email"])
        if Organization.objects.filter(slug=slug).exists():
            raise CommandError(f"Já existe uma organização com o slug '{slug}'.")
        if User.objects.filter(email=email).exists():
            raise CommandError(f"Já existe um usuário com o e-mail '{email}'.")

        password = options["admin_password"] or getpass.getpass("Senha do ADMIN: ")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        with transaction.atomic():
            organization = Organization.objects.create(name=options["name"], slug=slug)
            User.objects.create_user(
                email,
                password,
                organization=organization,
                role=Role.ADMIN,
                first_name=options["admin_first_name"],
            )

        self.stdout.write(
            self.style.SUCCESS(f"Organização '{organization.name}' criada; ADMIN: {email}")
        )

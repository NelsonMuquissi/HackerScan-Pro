from django.core.management.base import BaseCommand
from ai.models import CreditPackage, Achievement
from django.db import transaction

class Command(BaseCommand):
    help = 'Seeds AI Credit packages and achievements'

    def handle(self, *args, **options):
        self.stdout.write("Seeding AI Credit System...")
        
        with transaction.atomic():
            # Seed Packages
            packages = [
                {
                    "name": "Micro",
                    "slug": "micro",
                    "tagline": "Ideal para testes rápidos",
                    "credits": 500,
                    "bonus_credits": 0,
                    "price_usd": 1.99,
                    "sort_order": 1
                },
                {
                    "name": "Starter",
                    "slug": "starter",
                    "tagline": "Perfeito para desenvolvedores",
                    "credits": 1500,
                    "bonus_credits": 100,
                    "price_usd": 5.00,
                    "sort_order": 2
                },
                {
                    "name": "Growth",
                    "slug": "growth",
                    "tagline": "Para equipes em crescimento",
                    "credits": 7000,
                    "bonus_credits": 1000,
                    "price_usd": 20.00,
                    "sort_order": 3,
                    "is_featured": True,
                    "badge_text": "MELHOR VALOR"
                },
                {
                    "name": "Power",
                    "slug": "power",
                    "tagline": "Uso intensivo e análise profunda",
                    "credits": 20000,
                    "bonus_credits": 5000,
                    "price_usd": 50.00,
                    "sort_order": 4
                },
                {
                    "name": "Ultra",
                    "slug": "ultra",
                    "tagline": "Escala empresarial ilimitada",
                    "credits": 50000,
                    "bonus_credits": 15000,
                    "price_usd": 100.00,
                    "sort_order": 5
                },
            ]
            
            for p_data in packages:
                pkg, created = CreditPackage.objects.update_or_create(
                    slug=p_data["slug"],
                    defaults=p_data
                )
                if created:
                    self.stdout.write(f"Created package: {pkg.name}")

            # Seed Achievements
            achievements = [
                {
                    "slug": "first_steps",
                    "name": "Primeiros Passos",
                    "description": "Realize sua primeira análise de IA.",
                    "credits": 50,
                    "icon": "sparkles"
                },
                {
                    "slug": "curious_mind",
                    "name": "Mente Curiosa",
                    "description": "Peça 10 explicações de vulnerabilidades.",
                    "credits": 100,
                    "icon": "search"
                },
                {
                    "slug": "problem_solver",
                    "name": "Problem Solver",
                    "description": "Gere 5 códigos de remediação.",
                    "credits": 150,
                    "icon": "tool"
                },
                {
                    "slug": "seer",
                    "name": "O Vidente",
                    "description": "Use a previsão de cadeia de ataque pela primeira vez.",
                    "credits": 200,
                    "icon": "eye"
                },
                {
                    "slug": "loyal_auditor",
                    "name": "Auditor Fiel",
                    "description": "Mantenha uma subscrição ativa por 3 meses.",
                    "credits": 500,
                    "icon": "shield"
                },
                {
                    "slug": "bug_hunter_apprentice",
                    "name": "Caçador Aprendiz",
                    "description": "Encontre e analise 50 vulnerabilidades com IA.",
                    "credits": 300,
                    "icon": "target"
                },
                {
                    "slug": "efficiency_pro",
                    "name": "Pró-Eficiência",
                    "description": "Use o modo Express em 20 análises.",
                    "credits": 250,
                    "icon": "zap"
                },
                {
                    "slug": "big_spender",
                    "name": "Investidor",
                    "description": "Adquira seu primeiro pacote de créditos.",
                    "credits": 100,
                    "icon": "credit-card"
                },
                {
                    "slug": "security_pioneer",
                    "name": "Pioneiro de Segurança",
                    "description": "Seja um dos primeiros 1000 usuários do sistema de IA.",
                    "credits": 1000,
                    "icon": "award"
                },
                {
                    "slug": "master_of_intelligence",
                    "name": "Mestre da Inteligência",
                    "description": "Desbloqueie todas as outras conquistas básicas.",
                    "credits": 2500,
                    "icon": "crown"
                },
            ]

            for a_data in achievements:
                ach, created = Achievement.objects.update_or_create(
                    slug=a_data["slug"],
                    defaults=a_data
                )
                if created:
                    self.stdout.write(f"Created achievement: {ach.name}")

        self.stdout.write(self.style.SUCCESS("Successfully seeded AI Credit System!"))

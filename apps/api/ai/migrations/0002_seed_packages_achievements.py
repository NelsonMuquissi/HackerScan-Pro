"""
Seed data migration: 5 credit packages and 10 achievements.
Values match the monetization spec exactly.
"""
from django.db import migrations


def seed_credit_packages(apps, schema_editor):
    CreditPackage = apps.get_model("ai", "CreditPackage")
    packages = [
        {
            "name": "Micro",
            "slug": "micro",
            "tagline": "Para experimentar",
            "credits": 100,
            "bonus_credits": 0,
            "price_usd": "1.99",
            "is_featured": False,
            "badge_text": "",
            "sort_order": 0,
        },
        {
            "name": "Starter",
            "slug": "starter",
            "tagline": "Para uso ocasional",
            "credits": 500,
            "bonus_credits": 0,
            "price_usd": "5.00",
            "is_featured": False,
            "badge_text": "",
            "sort_order": 1,
        },
        {
            "name": "Growth",
            "slug": "growth",
            "tagline": "O mais popular",
            "credits": 2000,
            "bonus_credits": 200,
            "price_usd": "20.00",
            "is_featured": True,
            "badge_text": "⭐ Popular",
            "sort_order": 2,
        },
        {
            "name": "Power",
            "slug": "power",
            "tagline": "Para equipas activas",
            "credits": 5000,
            "bonus_credits": 1000,
            "price_usd": "50.00",
            "is_featured": False,
            "badge_text": "+20% bónus",
            "sort_order": 3,
        },
        {
            "name": "Ultra",
            "slug": "ultra",
            "tagline": "Melhor custo-benefício",
            "credits": 10000,
            "bonus_credits": 5000,
            "price_usd": "100.00",
            "is_featured": False,
            "badge_text": "Melhor valor",
            "sort_order": 4,
        },
    ]
    for pkg_data in packages:
        CreditPackage.objects.update_or_create(
            slug=pkg_data["slug"],
            defaults=pkg_data,
        )


def seed_achievements(apps, schema_editor):
    Achievement = apps.get_model("ai", "Achievement")
    achievements = [
        ("first_scan", "Primeiro Scan", "Completaste o teu primeiro scan", "🔍", 50),
        ("five_scans", "Caçador de Vulns", "Completaste 5 scans", "🎯", 100),
        ("twenty_scans", "Scanner Profissional", "Completaste 20 scans", "⚡", 200),
        ("first_critical", "Alerta Máximo", "Encontraste uma vulnerabilidade crítica", "🚨", 150),
        ("first_report", "Primeiro Relatório", "Geraste o teu primeiro relatório PDF", "📄", 75),
        ("invite_teammate", "Team Player", "Convidaste um membro para a equipa", "👥", 200),
        ("thirty_day_streak", "Streak 30 dias", "Usaste HackScan 30 dias consecutivos", "🔥", 500),
        ("first_bounty", "Bug Hunter", "Submeteste o teu primeiro bug bounty", "💰", 300),
        ("first_fix", "Remediation Hero", "Marcaste um finding como corrigido", "✅", 50),
        ("referral_success", "Embaixador", "O teu referral fez upgrade para pago", "🌟", 500),
    ]
    for slug, name, description, icon, credits in achievements:
        Achievement.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "icon": icon,
                "credits": credits,
                "is_active": True,
            },
        )


def reverse_seed(apps, schema_editor):
    apps.get_model("ai", "CreditPackage").objects.all().delete()
    apps.get_model("ai", "Achievement").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_create_ai_credit_models"),
    ]

    operations = [
        migrations.RunPython(seed_credit_packages, reverse_seed),
        migrations.RunPython(seed_achievements, reverse_seed),
    ]

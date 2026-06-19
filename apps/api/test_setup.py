import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
print("Setting up django...")
django.setup()
print("Django setup complete.")

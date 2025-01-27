from django.db import migrations
import traceback
import dataclasses
import main.uic
import main.ticket
import main.models

def uic_signature(apps, schema_editor):
    model = apps.get_model("main", "UICTicketInstance")
    for i in model.objects.all():
        try:
            t = main.models.UICTicketInstance.as_ticket(i)
        except main.ticket.TicketError:
            traceback.print_exc()
            continue
        if not t.envelope.signed_data:
            e = main.uic.Envelope.parse(t.raw_bytes)
            i.decoded_data["envelope"] = dataclasses.asdict(e, dict_factory=main.ticket.to_dict_json)
            i.save()


class Migration(migrations.Migration):
    atomic = False
    
    dependencies = [
        ('main', '0043_swisspassticketinstance'),
    ]

    operations = [
        migrations.RunPython(uic_signature, lambda a, s: None),
    ]

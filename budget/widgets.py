from django.forms.models import ModelChoiceField
from django.utils.encoding import force_text

class PrefixedModelChoiceField(ModelChoiceField):
    def __init__(self, prefix="", *args, **kwargs):
        self.prefix = force_text(prefix)
        super(PrefixedModelChoiceField, self).__init__(*args, **kwargs)

    def render_option(self, selected_choices, option_value, option_label):
        option_label = self.prefix+force_text(option_label)
        return super(PrefixedModelChoiceField, self).render_option(
                selected_choices, option_value, option_label)


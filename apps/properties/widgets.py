from django.forms import HiddenInput
from django.utils.html import format_html


class MapCoordinateWidget(HiddenInput):
    def __init__(self, *, map_name: str, axis: str, attrs=None):
        self.map_name = map_name
        self.axis = axis
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = {
            **(attrs or {}),
            "data-map-coordinate": self.map_name,
            "data-map-axis": self.axis,
        }
        hidden = super().render(name, value, attrs, renderer)
        if self.axis != "latitude":
            return hidden
        title = "Public map pin" if self.map_name == "public" else "Private exact map pin"
        help_text = (
            "Click the map to choose the location visitors may see."
            if self.map_name == "public"
            else (
                "Click the map to record the exact internal location. "
                "This pin is never sent to public pages."
            )
        )
        return format_html(
            '{}<section class="lala-map-picker" data-map-picker="{}"><h3>{}</h3>'
            '<p>{}</p><div class="lala-map-canvas" aria-label="{}"></div>'
            '<p class="lala-map-readout" aria-live="polite">No pin selected</p>'
            '<button class="button button-secondary lala-map-clear" type="button">'
            "Clear pin</button></section>",
            hidden,
            self.map_name,
            title,
            help_text,
            title,
        )

    class Media:
        css = {
            "all": (
                "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
                "css/location-map-admin.css",
            )
        }
        js = (
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
            "js/location-map-admin.js",
        )

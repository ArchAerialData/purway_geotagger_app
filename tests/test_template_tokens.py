from purway_geotagger.templates.models import RenameTemplate
from purway_geotagger.templates.template_manager import render_filename

def test_render_filename():
    t = RenameTemplate(id="t", name="t", client="ACME", pattern="{client}_{index:03d}_{ppm}ppm_{orig}")
    out = render_filename(t, index=7, ppm=12.3, lat=1.0, lon=2.0, orig="IMG_0001")
    assert out.startswith("ACME_007_12ppm_IMG_0001")

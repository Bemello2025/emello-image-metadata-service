from flask import Flask, request, jsonify
from PIL import Image
from iptcinfo3 import IPTCInfo
import piexif
import io
import base64
import tempfile
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Image Metadata Service is live."

@app.route('/write-metadata', methods=['POST'])
def write_metadata():
    try:
        data = request.json
        base64_str = data.get("image_base64")
        if not base64_str:
            return jsonify({"error": "Missing image_base64"}), 400

        # Standard metadata
        alt_text = data.get("alt_text")
        title_tag = data.get("title_tag")
        description = data.get("cms_description")

        # Advanced IPTC fields
        object_name = data.get("object_name")
        keywords = data.get("keywords", "").split(",") if data.get("keywords") else []
        subject_code = data.get("subject_code")
        byline = data.get("byline")
        copyright_notice = data.get("copyright_notice")

        # Convert base64 to PIL image
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))

        # Save temporarily for IPTC writing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            image.save(tmp.name, format="JPEG")

        # ✅ Inject IPTC metadata
        info = IPTCInfo(tmp.name, force=True)
        if object_name: info['object name'] = object_name
        if keywords: info['keywords'] = [kw.strip() for kw in keywords]
        if subject_code: info['subject reference'] = subject_code
        if byline: info['by-line'] = byline
        if copyright_notice: info['copyright notice'] = copyright_notice
        info.save()

        # ✅ Reload to memory
        with open(tmp.name, "rb") as f:
            final_base64 = base64.b64encode(f.read()).decode("utf-8")

        # Clean up
        os.unlink(tmp.name)

        return jsonify({
            "image_base64": final_base64
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

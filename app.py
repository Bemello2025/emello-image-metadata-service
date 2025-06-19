
from flask import Flask, request, jsonify
from PIL import Image
from io import BytesIO
import base64
import piexif

app = Flask(__name__)

@app.route('/write-metadata', methods=['POST'])
def write_metadata():
    data = request.get_json()
    if not data or "image_base64" not in data or "metadata" not in data:
        return jsonify({"error": "Missing image_base64 or metadata"}), 400

    try:
        # Decode base64 image
        image_data = base64.b64decode(data["image_base64"])
        image = Image.open(BytesIO(image_data))

        # Build metadata (using EXIF UserComment)
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        meta = data["metadata"]
        user_comment = f"alt={meta.get('alt_text', '')}; title={meta.get('title_tag', '')}; desc={meta.get('cms_description', '')}"
        exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(user_comment, encoding="unicode")

        # Insert metadata
        exif_bytes = piexif.dump(exif_dict)
        output = BytesIO()
        image.save(output, format="JPEG", exif=exif_bytes)
        encoded_image = base64.b64encode(output.getvalue()).decode()

        return jsonify({"image_base64": encoded_image})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

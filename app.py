@app.route('/write-metadata', methods=['POST'])
def write_metadata():
    data = request.json
    base64_str = data.get("image_base64")
    alt_text = data.get("alt_text") or ""
    title_tag = data.get("title_tag") or ""
    description = data.get("cms_description") or ""

    if not base64_str:
        return jsonify({"error": "Missing image_base64"}), 400

    image_data = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_data))

    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    # Correct mapping and encoding
    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = alt_text  # plain string
    exif_dict["0th"][piexif.ImageIFD.XPTitle] = title_tag.encode("utf-16le")
    exif_dict["0th"][piexif.ImageIFD.XPComment] = description.encode("utf-16le")

    exif_bytes = piexif.dump(exif_dict)

    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif_bytes)
    encoded_img = base64.b64encode(output.getvalue()).decode("utf-8")

    return jsonify({"image_base64": encoded_img})

import os

base_dir = r"c:\Users\dell\Downloads\Medical Job Portal\Medical Job Portal\medical_job_portal"

files_to_update = [
    r"users\templates\users\login.html",
    r"doctors\templates\doctors\base.html",
    r"nurses\templates\nurses\base.html",
    r"hospitals\templates\hospitals\base.html",
    r"admin_panel\templates\admin_panel\base.html",
]

head_tags = """
    <link rel="manifest" href="{% url 'manifest' %}">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="theme-color" content="#0056b3">
</head>
"""

body_tags = """
<script>
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register("{% url 'serviceworker' %}").then(function(registration) {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            }, function(err) {
                console.log('ServiceWorker registration failed: ', err);
            });
        });
    }
</script>
</body>
"""

for rel_path in files_to_update:
    filepath = os.path.join(base_dir, rel_path)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated = False
        if "</head>" in content and "manifest.json" not in content and "{% url 'manifest' %}" not in content:
            content = content.replace("</head>", head_tags)
            updated = True
        
        if "</body>" in content and "serviceWorker" not in content:
            content = content.replace("</body>", body_tags)
            updated = True
            
        if updated:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {rel_path}")
        else:
            print(f"Skipped {rel_path} (already updated or tags not found)")
    else:
        print(f"File not found: {rel_path}")

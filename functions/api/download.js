export async function onRequestGet(context) {
  try {
    const url = new URL(context.request.url);
    const file = url.searchParams.get("file");

    if (!file || !file.endsWith(".csv")) {
      return new Response("Missing CSV filename.", { status: 400 });
    }

    const env = context.env;
    const owner = env.GITHUB_OWNER;
    const repo = env.GITHUB_REPO;
    const ref = env.GITHUB_REF || "main";
    const token = env.GITHUB_TOKEN;

    if (!owner || !repo || !token) {
      return new Response("GitHub settings missing in Cloudflare.", { status: 500 });
    }

    const path = `exports/${file}`;
    const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path).replaceAll("%2F", "/")}?ref=${encodeURIComponent(ref)}`;

    const response = await fetch(apiUrl, {
      headers: {
        "accept": "application/vnd.github+json",
        "authorization": `Bearer ${token}`,
        "user-agent": "retail-address-finder"
      }
    });

    if (!response.ok) {
      const text = await response.text();
      return new Response(`Could not fetch file: ${text}`, { status: response.status });
    }

    const data = await response.json();
    const base64 = data.content.replace(/\n/g, "");
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);

    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }

    return new Response(bytes, {
      status: 200,
      headers: {
        "content-type": "text/csv; charset=utf-8",
        "content-disposition": `attachment; filename="${file}"`
      }
    });
  } catch (error) {
    return new Response(error.message || "Download failed.", { status: 500 });
  }
}

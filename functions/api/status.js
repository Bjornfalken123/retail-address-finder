export async function onRequestGet(context) {
  try {
    const url = new URL(context.request.url);
    const file = url.searchParams.get("file");

    if (!file || !file.endsWith(".csv")) {
      return json({ error: "Missing CSV filename." }, 400);
    }

    const env = context.env;
    const owner = env.GITHUB_OWNER;
    const repo = env.GITHUB_REPO;
    const ref = env.GITHUB_REF || "main";
    const token = env.GITHUB_TOKEN;

    const path = `exports/${file}`;

    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path).replaceAll("%2F", "/")}?ref=${encodeURIComponent(ref)}`,
      {
        headers: {
          "accept": "application/vnd.github+json",
          "authorization": `Bearer ${token}`,
          "user-agent": "retail-address-finder"
        }
      }
    );

    if (response.status === 404) {
      return json({
        ready: false,
        status: "running",
        message: "Exporten körs fortfarande."
      });
    }

    if (!response.ok) {
      const text = await response.text();
      return json({ error: `GitHub svarade ${response.status}: ${text}` }, 500);
    }

    const data = await response.json();

    return json({
      ready: true,
      status: "ready",
      file,
      size: data.size,
      downloadUrl: `/api/download?file=${encodeURIComponent(file)}`
    });

  } catch (error) {
    return json({ error: error.message || "Okänt fel." }, 500);
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8"
    }
  });
}

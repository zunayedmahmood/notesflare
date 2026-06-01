/** @type {import('next').NextConfig} */
const nextConfig = {
  // NotesFlare now uses the Next.js server during desktop development/runtime.
  // Static export can be re-enabled for packaging experiments by setting
  // NOTESFLARE_STATIC_EXPORT=1, but it is intentionally not the default because
  // unbounded archive routes do not fit static pre-generation well.
  ...(process.env.NOTESFLARE_STATIC_EXPORT === "1"
    ? {
        output: "export",
        trailingSlash: true,
        assetPrefix: "./",
      }
    : {}),
};

module.exports = nextConfig;

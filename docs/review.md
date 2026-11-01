# Review notes

Updated: 1 November 2026.

- Public distribution: `club-management==0.1.0`, imported as `club_management`,
  under MIT; confirm name availability and the copyright notice before release.
- Shared code consists of functions; authentication and resource objects come
  directly from `1password` and `O365`.
- Credentials use a complete environment pair first and 1Password only when
  neither variable is set; verify the configured field IDs and leave both
  variables absent on a Mac using the signed-in CLI.
- Select application or delegated Microsoft access per application, scope its
  permissions, and keep persistent token files private.
- Reading mail does not acknowledge it; the application marks messages as read
  after successful processing and handles any retries or checkpoints.
- Attachments use native O365 objects and remain in memory; uploads fail on
  conflicts unless the caller chooses another policy.
- Logging uses UTC and optional 5 MB files with five backups; choose a private
  location and retention, and do not log secrets or member data.
- The package supplies no web login, job queue, schedules, or business rules.
- Tests cover shared credential, mail, upload, filename, and logging behaviour
  with synthetic data; live Microsoft access and 1Password items need a
  controlled verification before unattended operation.
- Nothing has been committed, published, or installed; consumers must resolve
  their lockfiles after the intended public release exists.

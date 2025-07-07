# SpamScoreTracker DirectAdmin Plugin

This plugin provides a simple interface for DirectAdmin administrators to review SpamAssassin scores for incoming email. It parses the Exim mail log and lists the score for each message, recording extra details such as the subject, message ID, size, and whether the message was delivered or rejected.

*Requires the Evolution skin.*

## Installation

1. Copy the `spam_score_tracker` directory to `/usr/local/directadmin/plugins/`.
2. Run the provided `scripts/install.sh` script from inside the directory to create the log folder and set permissions.
3. Ensure the directory ownership is `diradmin:diradmin` if not already set.
4. Log in to DirectAdmin as admin and navigate to *Plugins* to enable **SpamScoreTracker**.

To remove the plugin cleanly, run `./scripts/uninstall.sh` from the plugin directory before deleting it.

By default the plugin reads `/var/log/exim/mainlog` and `/var/log/mail.log`.  Edit the `$logFiles` array in `public_html/index.php` if your logs are stored in different locations. Parsed results are written to `logs/scores.log` inside the plugin directory for later review. Each line of the CSV file includes the date, message ID, sender, recipients, IP, score, the triggered SpamAssassin tests, subject, message ID, size, the raw SpamAssassin line, and whether the message was delivered or rejected. The parser cross-references SpamAssassin logs with Exim entries by the email's Message-ID so that scores from `spamd` lines are matched to the correct delivery record.

### Packaging

The repository does not include the plugin archive. To create `spam_score_tracker.tar.gz` in the repository root for upload, run:

```sh
./build_plugin.sh
```

An optional `update_plugin.sh` script is provided to rebuild and install the plugin on a local DirectAdmin server in one step.

## Troubleshooting

If the panel shows "No spam scores were parsed" or entries with *No score*, the log files are missing SpamAssassin results. Check the following:

1. Confirm that the paths listed in `$logFiles` inside `public_html/index.php` match your system's log locations.
2. Ensure Exim is configured to log spam results. The `log_selector` option should include `+spam_score` and related settings so lines such as `spamcheck: score=` appear in the log.
3. When relying on `spamd` logs, start `spamd` with the `-L` (`--log-id`) option so message IDs are recorded. Without this, the plugin cannot correlate scores to messages.
4. Spamd result lines that appear before the matching Exim entry are cached using the Message-ID and applied once the delivery is seen.
5. The parser will fall back to the last Exim ID when a SpamAssassin line lacks a `mid=<...>` tag, but concurrent deliveries can still lead to mismatches.

After adjusting the configuration, reload the mail services and revisit the plugin page.

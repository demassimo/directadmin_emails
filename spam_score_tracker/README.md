# SpamScoreTracker DirectAdmin Plugin

This plugin provides a simple interface for DirectAdmin administrators to review SpamAssassin scores for incoming email. It parses the Exim mail log and lists the score for each message, recording extra details such as the subject, message ID, size, and whether the message was delivered or rejected.

*Requires the Evolution skin.*

## Installation

1. Copy the `spam_score_tracker` directory to `/usr/local/directadmin/plugins/`.
2. Run the provided `scripts/install.sh` script from inside the directory. The script creates the log folder, installs Python and required modules, reads MySQL credentials from `/usr/local/directadmin/conf/mysql.conf` to set up the `mail_logs` database (user `mail_logs`, password `l59X8bHfO07FIBWY08Z98`), and installs a systemd unit to keep the database updated from the mail logs.
3. Ensure the directory ownership is `diradmin:diradmin` if not already set.
4. Log in to DirectAdmin as admin and navigate to *Plugins* to enable **SpamScoreTracker**.

To remove the plugin cleanly, run `./scripts/uninstall.sh` from the plugin directory before deleting it.

The included Python script continuously tails `/var/log/exim/mainlog` and `/var/log/mail.log` and stores each message's score along with the sender, recipients and subject in a MySQL table. The PHP interface simply reads from this database, so no log parsing is done on each page load.

The web interface lets you choose how many results to display per page and offers page numbers to navigate through the history. Each entry includes a **View** link which shows 20 lines of log context around the spam-check entry for that message.

### Packaging

The repository does not include the plugin archive. To create `spam_score_tracker.tar.gz` in the repository root for upload, run:

```sh
./build_plugin.sh
```

An optional `update_plugin.sh` script is provided to rebuild and install the plugin on a local DirectAdmin server in one step.

### Command-line queries

The `scripts/spam_score_tool.py` helper can store and retrieve scores in a
MySQL database. Edit the `DB_CONFIG` section at the top of the script with your
database credentials, then run:

```sh
python3 scripts/spam_score_tool.py backfill
```
to import any existing log entries. You can then look up a single message by
ID and timestamp or start continuous tracking with:

```sh
python3 scripts/spam_score_tool.py follow
```

Once running, the service will keep the database in sync. You can still look up
a single message manually:

```sh
python3 scripts/spam_score_tool.py query --mid "<message-id>" --time "YYYY/MM/DD HH:MM"
```

## Troubleshooting

If the panel shows "No spam scores were parsed" or entries with *No score*, the log files are missing SpamAssassin results. Check the following:

1. Confirm that the paths listed in `$logFiles` inside `public_html/index.php` match your system's log locations.
2. Ensure Exim is configured to log spam results. The `log_selector` option should include `+spam_score` and related settings so lines such as `spamcheck: score=` appear in the log.
3. When relying on `spamd` logs, start `spamd` with the `-L` (`--log-id`) option so message IDs are recorded. Without this, the plugin cannot correlate scores to messages.
4. Spamd result lines that appear before the matching Exim entry are cached using the Message-ID and applied once the delivery is seen.
5. The parser will fall back to the last Exim ID when a SpamAssassin line lacks a `mid=<...>` tag, but concurrent deliveries can still lead to mismatches.

After adjusting the configuration, reload the mail services and revisit the plugin page.

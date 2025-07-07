# SpamScoreTracker DirectAdmin Plugin

This plugin provides a simple interface for DirectAdmin administrators to review SpamAssassin scores for incoming email. It parses the Exim mail log and lists the score for each message, recording extra details such as the subject, message ID, size, and whether the message was delivered or rejected.

*Requires the Evolution skin.*

## Installation

1. Copy the `spam_score_tracker` directory to `/usr/local/directadmin/plugins/`.
2. Run the provided `install.sh` script from inside the directory to create the log folder and set permissions.
3. Ensure the directory ownership is `diradmin:diradmin` if not already set.
4. Log in to DirectAdmin as admin and navigate to *Plugins* to enable **SpamScoreTracker**.

To remove the plugin cleanly, run `./uninstall.sh` from the plugin directory before deleting it.

The plugin parses `/var/log/exim/mainlog`. Adjust the path in `public_html/index.php` if your Exim log is located elsewhere. Parsed results are written to `logs/scores.log` inside the plugin directory for later review. Each line of the CSV file includes the date, message ID, sender, recipients, IP, score, subject, message ID, size, the raw SpamAssassin line, and whether the message was delivered or rejected.

### Packaging

The repository does not include the plugin archive. To create `spam_score_tracker.tar.gz` for upload, run:

```sh
./build_plugin.sh
```

<?php
// SpamScoreTracker admin page
// Only accessible to an administrator
$user = $_SERVER['REMOTE_USER']
    ?? $_SERVER['username']
    ?? $_SERVER['USER']
    ?? $_SERVER['user']
    ?? '';
$allowedAdmins = ['admin', 'diradmin'];
if ($user === '' || !in_array($user, $allowedAdmins, true)) {
    header('HTTP/1.1 403 Forbidden');
    echo 'Access denied';
    exit;
}

// Path to Exim main log (adjust if necessary)
$logFile = '/var/log/exim/mainlog';

// Where to store parsed data
$logOutput = __DIR__ . '/../logs/scores.log';

function parse_log($file) {
    if (!file_exists($file)) return [];
    $fh = fopen($file, 'r');
    if (!$fh) return [];
    $msg = [];
    while (($line = fgets($fh)) !== false) {
        // message received line
        if (preg_match('/^(\S+\s+\S+)\s+(\S+)\s+<=\s+(\S+).*\[(\d+\.\d+\.\d+\.\d+)\]/', $line, $m)) {
            $id = $m[2];
            $msg[$id]['time'] = $m[1];
            $msg[$id]['from'] = $m[3];
            $msg[$id]['ip'] = $m[4];
            if (preg_match('/T="([^"]*)"/', $line, $ms)) {
                $msg[$id]['subject'] = $ms[1];
            }
            if (preg_match('/id=([^\s]+)/', $line, $mi)) {
                $msg[$id]['msgid'] = $mi[1];
            }
            if (preg_match('/S=(\d+)/', $line, $msz)) {
                $msg[$id]['size'] = $msz[1];
            }
        }

        // delivery lines
        if (preg_match('/^(\S+\s+\S+)\s+(\S+)\s+=>\s+(\S+)/', $line, $m)) {
            $id = $m[2];
            $msg[$id]['to'][] = $m[3];
        }

        // completed delivery line
        if (preg_match('/^(\S+\s+\S+)\s+(\S+)\s+Completed/', $line, $m)) {
            $id = $m[2];
            $msg[$id]['action'] = $msg[$id]['action'] ?? 'delivered';
        }

        // rejection line
        if (preg_match('/^(\S+\s+\S+)\s+(\S+).*rejected/i', $line, $m)) {
            $id = $m[2];
            $msg[$id]['action'] = 'rejected';
        }

        // spam score line
        // Match variations like "spamcheck:" or "spamcheck result:" so the
        // score is captured even if the wording differs between servers.
        if (preg_match('/^(\S+\s+\S+)\s+(\S+)\s+.*score=([\d\.\-]+)/i', $line, $m)) {
            $id = $m[2];
            $msg[$id]['time'] = $msg[$id]['time'] ?? $m[1];
            $msg[$id]['score'] = floatval($m[3]);
            $msg[$id]['spamline'] = trim($line);
        }
    }
    fclose($fh);
    return $msg;
}


$scores = parse_log($logFile);

// Determine action for each message based on log lines
foreach ($scores as $id => $info) {
    if (!empty($info['action'])) continue;
    $scores[$id]['action'] = 'delivered';
}

// Write the parsed data to a log file for later review
if (!empty($scores)) {
    if (!is_dir(dirname($logOutput))) {
        mkdir(dirname($logOutput), 0755, true);
    }
    if ($fh = fopen($logOutput, 'a')) {
        foreach ($scores as $id => $info) {
            $to = isset($info['to']) ? implode(',', $info['to']) : '';
            fputcsv($fh, [
                $info['time'] ?? '',
                $id,
                $info['from'] ?? '',
                $to,
                $info['ip'] ?? '',
                $info['score'] ?? '',
                $info['subject'] ?? '',
                $info['msgid'] ?? '',
                $info['size'] ?? '',
                $info['spamline'] ?? '',
                $info['action'] ?? ''
            ]);
        }
        fclose($fh);
    }
}
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Spam Score Tracker</title>
    <style>
        /* Basic styling to mimic Evolution tables */
        body { margin: 20px; font-family: Arial, sans-serif; background: #f5f5f5; }
        .panel {
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 6px;
            overflow: hidden;
        }
        th, td { padding: 8px 10px; border: 1px solid #ddd; }
        th { background: #f7f7f7; }
        tr:nth-child(even) { background: #fafafa; }
        tr:hover { background: #f0f0f0; }
    </style>
</head>
<body>
<div class="panel">
<h1>SpamAssassin Score History</h1>

<table class="table table-striped table-bordered">
    <tr><th>Date</th><th>ID</th><th>From</th><th>To</th><th>IP</th><th>Score</th><th>Subject</th><th>Message ID</th><th>Size</th><th>Action</th></tr>
    <?php foreach ($scores as $id => $s): ?>
        <tr>
            <td><?php echo htmlspecialchars($s['time'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($id); ?></td>
            <td><?php echo htmlspecialchars($s['from'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars(isset($s['to']) ? implode(',', $s['to']) : ''); ?></td>
            <td><?php echo htmlspecialchars($s['ip'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars(isset($s['score']) ? $s['score'] : 'N/A'); ?></td>
            <td><?php echo htmlspecialchars($s['subject'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($s['msgid'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($s['size'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($s['action'] ?? ''); ?></td>
        </tr>
    <?php endforeach; ?>
</table>
</div>
</body>
</html>

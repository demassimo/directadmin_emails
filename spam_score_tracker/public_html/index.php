<?php
// SpamScoreTracker admin page using database
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

$dsn = 'mysql:host=127.0.0.1;dbname=mail_logs;charset=utf8mb4';
$dbu = 'mail_logs';
$dbp = 'l59X8bHfO07FIBWY08Z98';

    $snippet = '';
    if (!empty($_GET['snippet_mid'])) {
    $mid = preg_replace('/[^A-Za-z0-9._<>@-]/', '', $_GET['snippet_mid']);
    $escMid = escapeshellarg($mid);
    $grep = "grep -n $escMid /var/log/exim/mainlog* /var/log/mail.log* 2>/dev/null | head -1";
    $out = trim(shell_exec($grep));
    if ($out !== '') {
        list($file, $line) = explode(':', $out, 2);
        $line = (int)$line;
        $start = max(1, $line - 10);
        $end = $line + 10;
        if (substr($file, -3) === '.gz') {
            $cmd = "zcat " . escapeshellarg($file) . " | sed -n '{$start},{$end}p'";
        } else {
            $cmd = "sed -n '{$start},{$end}p' " . escapeshellarg($file);
        }
        $snippet = htmlspecialchars(shell_exec($cmd));
        $snippet = "<pre>" . $snippet . "</pre>";
    } else {
        $snippet = '<div class="alert">Log entry not found.</div>';
    }
}

// pagination parameters
$allowedPerPage = [10, 30, 50, 100, 500];
$perPage = isset($_GET['per_page']) ? (int)$_GET['per_page'] : 30;
if (!in_array($perPage, $allowedPerPage, true)) {
    $perPage = 30;
}
$page = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1;
$offset = ($page - 1) * $perPage;

try {
    $pdo = new PDO($dsn, $dbu, $dbp);
    $count = (int)$pdo->query('SELECT COUNT(*) FROM spam_scores')->fetchColumn();
    $stmt = $pdo->prepare('SELECT ts,message_id,sender,recipients,subject,score '
        .'FROM spam_scores ORDER BY ts DESC LIMIT :lim OFFSET :off');
    $stmt->bindValue(':lim', $perPage, PDO::PARAM_INT);
    $stmt->bindValue(':off', $offset, PDO::PARAM_INT);
    $stmt->execute();
    $scores = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    $scores = [];
    $count = 0;
}
$totalPages = $perPage ? (int)ceil($count / $perPage) : 1;
$allMissingScores = empty($scores);
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Spam Score Tracker</title>
    <style>
        body { margin: 20px; font-family: Arial, sans-serif; background: #f5f5f5; }
        .panel { max-width: 800px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 6px; overflow: hidden; }
        th, td { padding: 8px 10px; border: 1px solid #ddd; }
        th { background: #f7f7f7; }
        tr:nth-child(even) { background: #fafafa; }
        .alert { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .pagination a { margin: 0 3px; text-decoration: none; }
        pre { background: #f0f0f0; padding: 10px; border-radius: 4px; }
    </style>
</head>
<body>
<div class="panel">
<h1>SpamAssassin Score History</h1>
<form method="get" style="margin-bottom:10px">
    <label for="per_page">Results per page:</label>
    <select id="per_page" name="per_page" onchange="this.form.submit()">
        <?php foreach ($allowedPerPage as $n): ?>
        <option value="<?php echo $n; ?>"<?php if ($perPage==$n) echo ' selected'; ?>><?php echo $n; ?></option>
        <?php endforeach; ?>
    </select>
</form>
<div id="snippet">
<?php echo $snippet; ?>
</div>
<?php if ($allMissingScores): ?>
<div class="alert">No spam scores were found in the database.</div>
<?php endif; ?>
<div id="results">
<table class="table table-striped table-bordered">
    <tr><th>Date</th><th>From</th><th>To</th><th>Subject</th><th>Message ID</th><th>Score</th><th>Log</th></tr>
    <?php foreach ($scores as $s): ?>
        <tr>
            <td><?php echo htmlspecialchars($s['ts']); ?></td>
            <td><?php echo htmlspecialchars($s['sender'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($s['recipients'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($s['subject'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($s['message_id'] ?? ''); ?></td>
            <td><?php echo htmlspecialchars($s['score']); ?></td>
            <td><a href="?snippet_mid=<?php echo urlencode($s['message_id']); ?>&page=<?php echo $page; ?>&per_page=<?php echo $perPage; ?>#snippet">View</a></td>
        </tr>
    <?php endforeach; ?>
</table>
<?php if ($totalPages > 1): ?>
<div class="pagination" style="margin-top:10px; text-align:center;">
    <?php for ($i = 1; $i <= $totalPages; $i++): ?>
        <?php if ($i == $page): ?>
            <strong><?php echo $i; ?></strong>
        <?php else: ?>
            <a href="?page=<?php echo $i; ?>&per_page=<?php echo $perPage; ?>#results"><?php echo $i; ?></a>
        <?php endif; ?>
        <?php if ($i < $totalPages) echo ' '; ?>
    <?php endfor; ?>
</div>
<?php endif; ?>
</div>
</div>
</body>
</html>

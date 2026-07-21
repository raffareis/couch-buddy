import time

from couch_buddy.state.watcher import SaveWatcher


def test_watcher_debounce_dispara_uma_vez(tmp_path):
    fired = []
    watcher = SaveWatcher(tmp_path, fired.append, debounce_s=0.3)
    watcher.start()
    try:
        target = tmp_path / "Auto_1.zks"
        target.write_bytes(b"chunk1")
        time.sleep(0.1)
        with target.open("ab") as f:
            f.write(b"chunk2")
        time.sleep(1.0)
        assert fired == [target]

        (tmp_path / "ignorar.tmp").write_bytes(b"x")
        time.sleep(0.5)
        assert len(fired) == 1
    finally:
        watcher.stop()

(defun my/screenshot-sorting-rules-move-matching-rules-to-bottom (folder)
  "in a rules file for sorting screenshots, enter a regex to move all matching rule lines to the bottom."
  (interactive "sRegex to match lines to be moved to the bottom of this file: ")
  (save-excursion
    (goto-char (point-min))
    (let ((pattern (concat "|\\s-*" (regexp-quote folder) "\\s-*$"))
          (matching-lines '()))
      ;; Collect and delete matching lines
      (while (re-search-forward pattern nil t)
        (let ((line (string-trim (thing-at-point 'line t))))
          (push line matching-lines)
          (delete-region (line-beginning-position) (line-beginning-position 2))))
      ;; Append to bottom if matches were found
      (when matching-lines
        (goto-char (point-max))
        (unless (bolp) (insert "\n"))
        (insert (format "\n# --- %s ---\n" folder))
        (dolq (line (nreverse matching-lines))
          (insert line "\n"))
        (message "Moved %d rules for '%s' to bottom." (length matching-lines) folder)))))

(defun my/dired-move-screenshot-with-sidecars ()
  "Move the .jpg at point along with its associated sidecars to the DWIM target directory."
  (interactive)
  (unless (derived-mode-p 'dired-mode)
    (user-error "This command can only be used in Dired mode"))
  (let* ((file (dired-get-filename nil t))
         (target-dir (dired-dwim-target-directory)))
    (unless file
      (user-error "No file on current line"))
    (unless target-dir
      (user-error "No target Dired window found in adjacent window split"))
    (if (not (string-match "\\(\\.jpg\\|\\.png\\|\\.webp\\)$" file))
        (message "File at point is not an image; skipping bundle move.")
      (let* ((dir (file-name-directory file))
             (filename (file-name-nondirectory file))
             ;; Extract base prefix (e.g. "2026-08-31-18:29-56_465x195.jpg")
             (base-name (if (string-match "^\\(.*?\\.\\(?:jpg\\|png\\|webp\\)\\)" filename)
                            (match-string 1 filename)
                          filename))
             ;; Find all files in current folder matching base-name prefix
             (matching-files (directory-files dir t (concat "^" (regexp-quote base-name))))
             (count (length matching-files)))
        (when (y-or-n-p (format "Move %d bundle file(s) for %s to %s? " 
                                count base-name target-dir))
          (dolist (src matching-files)
            (let ((dest (expand-file-name (file-name-nondirectory src) target-dir)))
              (rename-file src dest t)))
          (revert-buffer)
          ;; Optionally refresh destination buffer if active
          (when-let ((target-buf (car (delq nil (mapcar (lambda (w)
                                                          (let ((b (window-buffer w)))
                                                            (when (string= (with-current-buffer b default-directory) target-dir)
                                                              b)))
                                                        (window-list))))))
            (with-current-buffer target-buf
              (revert-buffer)))
          (message "Moved %d bundle file(s) to %s" count target-dir))))))

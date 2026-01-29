# Fix for test_analyze_elf_timeout_handled - line 137
# The message is "Import timed out" but "timed out" != "timeout"
# Change assertion to check for "timed out" instead

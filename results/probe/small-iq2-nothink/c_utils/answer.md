```c
uint32_t crc32_ieee(const uint8_t *data, size_t len)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            if (crc & 1u)
                crc = (crc >> 1) ^ 0xEDB88320u;
            else
                crc >>= 1;
        }
    }
    return crc ^ 0xFFFFFFFFu;
}

int parse_int32(const char *s, int32_t *out)
{
    if (s == NULL || *s == '\0')
        return -1;

    const char *p = s;
    int negative = 0;
    if (*p == '+' || *p == '-') {
        negative = (*p == '-');
        p++;
    }

    if (*p == '\0')
        return -1;

    uint32_t limit = negative ? ((uint32_t)INT32_MAX + 1u) : (uint32_t)INT32_MAX;
    uint32_t value = 0;

    while (*p != '\0') {
        if (!isdigit((unsigned char)*p))
            return -1;
        uint32_t digit = (uint32_t)(*p - '0');
        if (value > (limit - digit) / 10u)
            return -1;
        value = value * 10u + digit;
        p++;
    }

    if (negative) {
        if (value == (uint32_t)INT32_MAX + 1u)
            *out = INT32_MIN;
        else
            *out = -(int32_t)value;
    } else {
        *out = (int32_t)value;
    }
    return 0;
}

static void reverse_range(char *first, char *last)
{
    while (first < last) {
        char tmp = *first;
        *first = *last;
        *last = tmp;
        first++;
        last--;
    }
}

void reverse_words(char *s)
{
    if (s == NULL)
        return;

    size_t len = strlen(s);
    if (len == 0)
        return;

    reverse_range(s, s + len - 1);

    char *word_start = s;
    for (size_t i = 0; i <= len; i++) {
        if (s[i] == ' ' || s[i] == '\0') {
            if (i > 0)
                reverse_range(word_start, s + i - 1);
            word_start = s + i + 1;
        }
    }
}
```
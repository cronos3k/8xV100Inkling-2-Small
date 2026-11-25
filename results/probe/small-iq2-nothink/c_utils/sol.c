#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <limits.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>

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


#define CHECK(c) do { if (!(c)) { printf("FAILED line %d: %s\n", __LINE__, #c); return 1; } } while (0)
int main(void) {
    int32_t v = 77;
    CHECK(crc32_ieee((const uint8_t *)"123456789", 9) == 0xCBF43926u);
    CHECK(crc32_ieee((const uint8_t *)"", 0) == 0u);
    CHECK(crc32_ieee((const uint8_t *)"a", 1) == 0xE8B7BE43u);
    CHECK(parse_int32("2147483647", &v) == 0 && v == 2147483647);
    CHECK(parse_int32("-2147483648", &v) == 0 && v == INT32_MIN);
    CHECK(parse_int32("+7", &v) == 0 && v == 7);
    CHECK(parse_int32("-0", &v) == 0 && v == 0);
    CHECK(parse_int32("0000123", &v) == 0 && v == 123);
    v = 77;
    CHECK(parse_int32("2147483648", &v) == -1 && v == 77);
    CHECK(parse_int32("-2147483649", &v) == -1 && v == 77);
    CHECK(parse_int32("99999999999999999999", &v) == -1 && v == 77);
    CHECK(parse_int32("", &v) == -1 && v == 77);
    CHECK(parse_int32("+", &v) == -1 && v == 77);
    CHECK(parse_int32("-", &v) == -1);
    CHECK(parse_int32("12a", &v) == -1 && v == 77);
    CHECK(parse_int32(" 7", &v) == -1);
    CHECK(parse_int32("7 ", &v) == -1);
    CHECK(parse_int32("+-7", &v) == -1);
    char a[] = "the quick brown fox"; reverse_words(a); CHECK(strcmp(a, "fox brown quick the") == 0);
    char b[] = "a"; reverse_words(b); CHECK(strcmp(b, "a") == 0);
    char c[] = ""; reverse_words(c); CHECK(strcmp(c, "") == 0);
    char d[] = "ab cde"; reverse_words(d); CHECK(strcmp(d, "cde ab") == 0);
    puts("ALL-OK");
    return 0;
}

/*
 * Copyright 2019 Joshua Lackey.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License. * All rights reserved.
 */

#include "btchip_internal.h"
#include "btchip_apdu_constants.h"
#include "btchip_bagl_extensions.h"

#define CTX btchip_context_D

#define P1_ONLY 0xa5
#define P2_ONLY 0x5a

unsigned short btchip_apdu_sign_mnb_internal() {

    unsigned short sw = BTCHIP_SW_OK;
    unsigned char p1 = G_io_apdu_buffer[ISO_OFFSET_P1];
    unsigned char p2 = G_io_apdu_buffer[ISO_OFFSET_P2];
    unsigned char apduLength = G_io_apdu_buffer[ISO_OFFSET_LC];
    volatile unsigned short offset = ISO_OFFSET_CDATA;

    if (!os_global_pin_is_validated()) {
        return BTCHIP_SW_SECURITY_STATUS_NOT_SATISFIED;
    }

    if ((P1_ONLY != p1) || (P2_ONLY != p2)) {
        return BTCHIP_SW_INCORRECT_P1_P2;
    }

    BEGIN_TRY {
        TRY {
            // wipe old data
            os_memset(&CTX.mnc, 0, sizeof(CTX.mnc));

            if (apduLength < 1 + 4 * G_io_apdu_buffer[offset] + 36 + 16 + 2 + 2 * 33 + 8 + 4) {
                PRINTF("Not enough data\n");
                CLOSE_TRY;
                return BTCHIP_SW_INCORRECT_DATA;
            }
            if (G_io_apdu_buffer[offset] > MAX_BIP32_PATH) {
                PRINTF("Keypath too long\n");
                CLOSE_TRY;
                return BTCHIP_SW_INCORRECT_DATA;
            }

            // keypath
            os_memmove(CTX.mnc.mn_keypath, G_io_apdu_buffer + offset, G_io_apdu_buffer[offset] * 4 + 1);
            offset += G_io_apdu_buffer[offset] * 4 + 1;

            // hash mnb (leaving result in hash state); borrowing transactionHashAuthorization area
            cx_sha256_init(&CTX.transactionHashAuthorization);
            cx_hash(&CTX.transactionHashAuthorization.header, 0,
              G_io_apdu_buffer + offset, apduLength + ISO_OFFSET_CDATA - offset, NULL, 0);

            // ip (4 bytes)
            if ((G_io_apdu_buffer[offset + 36 + 10] != 0xff) || (G_io_apdu_buffer[offset + 36 + 11] != 0xff)) {
                PRINTF("Not IPv4?\n");
                CLOSE_TRY;
                return BTCHIP_SW_INCORRECT_DATA;
            }
            os_memmove(CTX.mnc.mn_ip, G_io_apdu_buffer + offset + 36 + 12, 4);

            CTX.io_flags |= IO_ASYNCH_REPLY;
            CLOSE_TRY;
            return BTCHIP_SW_OK;

        }
        CATCH_ALL {
            sw = SW_TECHNICAL_DETAILS(0x0F);
        }
        FINALLY {
            // wipe cached data
            os_memset(&CTX.mnc, 0, sizeof(CTX.mnc));
            return sw;
        }
    }
    END_TRY;
}

unsigned short btchip_apdu_sign_mnb() {
    unsigned short sw = btchip_apdu_sign_mnb_internal();

    if (CTX.io_flags & IO_ASYNCH_REPLY) {
        btchip_bagl_confirm_sign_mnb();
    }

    return sw;
}

unsigned short sign_mnb() {

    unsigned char hash[32];
    unsigned short sw = BTCHIP_SW_OK;

    BEGIN_TRY {
        TRY {
            // finish hashing and then hash again
            cx_hash(&CTX.transactionHashAuthorization.header, CX_LAST, hash, 0, hash, 32);
            cx_sha256_init(&CTX.transactionHashAuthorization);
            cx_hash(&CTX.transactionHashAuthorization.header, CX_LAST, hash, 32, hash, 32);

            // sign double-hash
            btchip_private_derive_keypair(CTX.mnc.mn_keypath, 0, NULL);
            btchip_signverify_finalhash(&btchip_private_key_D, 1, hash, 32, G_io_apdu_buffer, 128, 0);
            CTX.outLength = G_io_apdu_buffer[1] + 2;
        }
        CATCH_ALL {
            sw = SW_TECHNICAL_DETAILS(0x0f);
        }
        FINALLY {
        }
    }
    END_TRY;

    return sw;
}

void btchip_bagl_user_action_sign_mnb(unsigned char confirmed) {

    unsigned short sw;

    CTX.outLength = 0;

    if (confirmed) {
        sw = sign_mnb();
    } else {
        sw = BTCHIP_SW_CONDITIONS_OF_USE_NOT_SATISFIED;
    }

    G_io_apdu_buffer[CTX.outLength++] = sw >> 8;
    G_io_apdu_buffer[CTX.outLength++] = sw;

    io_exchange(CHANNEL_APDU | IO_RETURN_AFTER_TX, CTX.outLength);
}

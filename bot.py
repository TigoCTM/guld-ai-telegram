#!/usr/bin/env python
__version__ = '0.0.1'
import configparser
import json
import logging
import os
import string
from datetime import datetime
from io import StringIO, BytesIO
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Document)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
# from telegram.ext.dispatcher import run_async
from guldlib import *

config = configparser.ConfigParser()
config.read('config.ini')
COMMODITIES = json.loads(config['telegram']['COMMODITIES'])

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

NAMECHARS = set(string.ascii_lowercase + string.digits + '-')

UPLOADPGPKEY, SIGNTX, WELCOME, CANCEL = range(4)


def start(bot, update):
    en = (
            'Hi! My name is Gai, a guld-ai. I can help you with your guld related data and requests. I always respond from the perspective of guld founder, isysd.\n\n'
            'Commands:\n\n'
            '/price <unit>\n'
            '    - Price of a unit\n'
            '/bal <account> [unit]\n'
            '    - Account balance with optional unit\n'
            '/asl <account> [unit]\n'
            '    - Only assets & liabiliteis optional unit of account\n'
            '/addr <asset> <username>\n'  # TODO group or device
            '    - Get address from me. Deposits converted to GULD at market rate. (max 50)\n'
            '/register individual <name>\n'  # TODO group or device
            '    - Register as an individual.\n'
            '/send <from> <to> <amount> [commodity]\n'
            '    - Transfer to another account. Default unit is GULD.\n'
            '/grant <contributor> <amount> [commodity]\n'
            '    - Grant for contributors. Default unit is GULD.\n'
            '/sub <igned_tx>\n'
            '    - Submit a signed transaction\n'
            '/apply <username> <pgp-pub-key>\n'  # TODO group or device
            '    - Apply for an account with a username and PGP key (RSA 2048+ bit)\n'
        )
    es = (
            '¡Hola! Mi nombre es Gai, un guld-ai. Puedo ayudarte con tus datos y solicitudes relacionadas con guld. Siempre respondo desde la perspectiva del fundador de guld, isysd. \n\n'
            'Comandos: \n\n'
            '/price <unidad> \n'
            '    - Precio de un unidad \n'
            '/bal <cuenta> [unidad] \n'
            '    - Saldo de cuenta con unidad opcional \n'
            '/asl <cuenta> [unidad] \n'
            '    - Solo activos y pasivos es unidad opcional \n'
            '/addr <activo> <nombre> \n' # TODO grupo o dispositivo
            '    - Obtener dirección de mí. Depósitos convertidos a GULD a tasa de mercado. (max 50) \n'
            '/register individual <nombre> \n' # TODO grupo o dispositivo
            '    - Registrarse como individuo. \n'
            '/send <desde> <a> <cantidad> [unidad] \n'
            '    - Transferir a otra cuenta. La unidad predeterminada es GULD. \n'
            '/grant <contribuidor> <cantidad> [unidad] \n'
            '    - Grant para contribuyentes. La unidad predeterminada es GULD. \n'
            '/sub <igned_tx> \n'
            '    - Enviar una transacción firmada \n'
            '/apply <username> <pgp-pub-key> \n' # TODO grupo o dispositivo
            '    - Solicite una cuenta con un nombre de usuario y clave PGP (RSA 2048+ bit) \n'
        )
    if ' es' in update.message.text:
        update.message.reply_text(es)
    else:
        update.message.reply_text(en)
    return


def price(bot, update, args):
    # user = update.message.from_user
    if len(args) == 0:
        update.message.reply_text('Invalid commodity. Options are: %s' % ", ".join(COMMODITIES))
    else:
        commodity = str(args[0]).upper()
        if commodity not in COMMODITIES:
            update.message.reply_text('Invalid commodity. Options are: %s' % ", ".join(COMMODITIES))
        else:
            update.message.reply_text("%s = $%s" % (commodity, get_price(commodity)))
    return


def assets_liabilites(bot, update, args):
    if len(args) == 0:
        update.message.reply_text('username is required.')
    else:
        username = str(args[0])
        if len(args) > 1:
            bals = get_assets_liabs(username, in_commodity=str(args[1]))
        else:
            bals = get_assets_liabs(username)
        bals = (bals[:500] + '..') if len(bals) > 500 else bals
        update.message.reply_text(bals)
    return



def balance(bot, update, args):
    if len(args) == 0:
        update.message.reply_text('username is required.')
    else:
        username = str(args[0])
        if len(args) > 1:
            bals = get_balance(username, in_commodity=str(args[1]))
        else:
            bals = get_balance(username)
        bals = (bals[:500] + '..') if len(bals) > 500 else bals
        update.message.reply_text(bals)
    return


def register(bot, update, args):
    dt, tstamp = get_time_date_stamp()
    fname = '%s.dat' % tstamp
    utype = args[0]
    message = gen_register_individual(args[1], dt, tstamp)
    update.message.reply_document(document=BytesIO(str.encode(message)),
        filename=fname,
        caption="Please PGP sign the transaction file or text and send to the /txsub command:\n\n"
    )
    bot.send_message(chat_id=update.message.chat_id, text=message)
    return


def transfer(bot, update, args):
    dt, tstamp = get_time_date_stamp()
    fname = '%s.dat' % tstamp
    if len(args) > 3:
        commodity = args[3]
    else:
        commodity = 'GULD'
    message = gen_transfer(args[0], args[1], args[2], commodity, dt, tstamp)
    update.message.reply_document(document=BytesIO(str.encode(message)),
        filename=fname,
        caption="Please PGP sign the transaction file or text and send to the /txsub command:\n\n"
    )
    bot.send_message(chat_id=update.message.chat_id, text=message)
    return


def grant(bot, update, args):
    dt, tstamp = get_time_date_stamp()
    fname = '%s.dat' % tstamp
    amount = args[1]
    if len(args) > 2:
        commodity = args[2]
    else:
        commodity = 'GULD'

    message = gen_grant(args[0], args[1], commodity, dt, tstamp)
    update.message.reply_document(document=BytesIO(str.encode(message)),
        filename=fname,
        caption="Please PGP sign the transaction file or text and send to the /txsub command:\n\n"
    )
    bot.send_message(chat_id=update.message.chat_id, text=message)
    return


def application(bot, update, args):
    if len(args) < 2:
        update.message.reply_text('username and pgp pubkey are required arguments')
        return
    message = update.message.text[update.message.text.find(' '):].strip(' ')
    divi = message.find(' ')
    name = message[:divi].strip(' ').lower()
    pubkey = message[divi:].strip().replace('—', '--')
    if not all(c in NAMECHARS for c in name) or len(name) < 4:
        update.message.reply_text('Guld names must be at least 4 characters and can only have letters, numbers, and dashes (-).')
        return
    elif (len(pubkey) < 500 or
            not pubkey.startswith('-----BEGIN PGP PUBLIC KEY BLOCK-----') or
            not pubkey.endswith('-----END PGP PUBLIC KEY BLOCK-----')):
        update.message.reply_text('Please submit a valid, ascii-encoded PGP public key (RSA 2048+ bit) as a message.')
        return
    else:
        fpath = os.path.join(GULD_HOME, 'ledger', 'GULD', name)
        keypath = os.path.join(GULD_HOME, 'keys', 'pgp', name)
        try:
            os.makedirs(fpath)
            os.makedirs(keypath)
        except OSError as exc:
            if exc.errno == os.errno.EEXIST and os.path.isdir(os.path.join(GULD_HOME, 'ledger', 'GULD', name)):
                update.message.reply_text('That name is taken. Did you take it? Applying anyway, since we are in onboarding phase.')
            else:
                update.message.reply_text('Error reserving name. Try another one.')
            # return
        fpr = import_pgp_key(name, pubkey)
        if fpr is not None:
            update.message.reply_text('Application submitted, pending manual approval.\n\nname:        %s\nfingerprint: %s' % (name, fpr))
        else:
            update.message.reply_text('Unable to process application.')


def signed_tx(bot, update):
    if update.message.text != '/txsub':
        sigtext = update.message.text[7:].replace('—', '--')
        name = get_signer_name(sigtext)
        if name is None:
            update.message.reply_text('Invalid or untrusted signature.')
        else:
            rawtx = strip_pgp_sig(sigtext)
            txtype = get_transaction_type(rawtx)
            tstamp = get_transaction_timestamp(rawtx)
            if txtype is None:
                update.message.reply_text('ERROR: Unknown transaction type')
                return
            ac = get_transaction_amount(rawtx)
            if ac is None:
                update.message.reply_text('ERROR: Unknown transaction format')
                return
            amount, commodity = ac
            fname = '%s.dat' % tstamp
            fpath = os.path.join(GULD_HOME, 'ledger', commodity, name, fname)

            def write_tx_files():
                with open(fpath + '.asc', 'w') as sf:
                    sf.write(sigtext)
                    with open(fpath, 'w') as f:
                        f.write(rawtx)
                update.message.reply_text('Message submitted.')

            if os.path.exists(fpath):
                update.message.reply_text('Message already known.')
                return
            elif txtype == 'transfer':
                if not re.search(' *%s:Assets *%s %s*' % (name, amount, commodity), rawtx) or float(amount) >= 0:
                    update.message.reply_text('Cannot sign for account that is not yours.')
                    return
                else:
                    asl = get_assets_liabs(name)
                    aslbal = asl.strip().split('\n')[-1].strip().split(' ')[0]
                    if float(aslbal) + float(amount) < 0:
                        update.message.reply_text('Cannot create transction that would result in negative net worth.')
                        return
                write_tx_files()
            elif txtype == 'register individual':
                bal = get_guld_sub_bals(name)
                if 'guld:Income:register:individual' in bal:
                    update.message.reply_text('ERROR: Name already registered.')
                else:
                    write_tx_files()
            elif txtype == 'grant':
                if (float(amount) < 10 and name in ['fdreyfus', 'isysd', 'cz', 'juankong', 'goldchamp'] or
                    name in ['isysd', 'cz']):
                    write_tx_files()
    return


def get_addr(bot, update, args):
    commodity = args[0]
    if commodity not in ('BTC', 'DASH'):
        update.message.reply_text('only BTC and DASH are supported at the moment')
    else:
        counterparty = args[1]
        address = getAddresses(counterparty, 'isysd', commodity)[-1]
        update.message.reply_text(address)
    return


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    updater = Updater(config['telegram']['bottoken'])

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("price", price, pass_args=True))
    dp.add_handler(CommandHandler("bal", balance, pass_args=True))
    dp.add_handler(CommandHandler("asl", assets_liabilites, pass_args=True))
    dp.add_handler(CommandHandler("register", register, pass_args=True))
    dp.add_handler(CommandHandler("send", transfer, pass_args=True))
    dp.add_handler(CommandHandler("grant", grant, pass_args=True))
    dp.add_handler(CommandHandler("sub", signed_tx))
    dp.add_handler(CommandHandler("addr", get_addr, pass_args=True))
    dp.add_handler(CommandHandler("apply", application, pass_args=True))

    # register_handler = ConversationHandler(
    #     entry_points=[CommandHandler('register', register, pass_args=True)],
    #
    #     states={
    #         UPLOADPGPKEY: [MessageHandler(Filters.text, upload_pgp_key)],
    #         SIGNTX: [MessageHandler(Filters.text, signed_tx)],
    #         WELCOME: [MessageHandler(Filters.text, welcome_newuser)],
    #         CANCEL: [CommandHandler('cancel', cancel)]
    #     },
    #
    #     fallbacks=[CommandHandler('cancel', cancel)]
    # )
    #
    # dp.add_handler(register_handler)

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

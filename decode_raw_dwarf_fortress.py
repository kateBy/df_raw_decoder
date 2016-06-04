#!/usr/bin/python3

import zlib
from io import BytesIO
import os
from os.path import isfile, isdir, exists, realpath,\
                    split, splitext, join as joinPath

from_bytes = lambda x: int.from_bytes(x, byteorder="little")
from_int16 = lambda x: x.to_bytes(2, byteorder="little")
from_int32 = lambda x: x.to_bytes(4, byteorder="little")

debug = False

"""Функция декодирования текстового raw-файла"""
def decode_datafile(zipfile, txtfile):

    _zip = open(zipfile, 'rb')
    zip_length = from_bytes(_zip.read(4)) #Первые 4 байта - длина последующего архива
    deflate = _zip.read()
    _zip.close()

    if zip_length == len(deflate):
        #Обработка файла
        unpacked = zlib.decompress(deflate)
        buf = BytesIO()
        buf.write(unpacked)
        buf.seek(0)
        lines_count = from_bytes(buf.read(4)) #Первые 4 байта - кол-во строк
        result = []
        
        file_path, fn = split(zipfile)
        indexFile = False
        if fn == 'index': #Файл index имеет туже структуру, но немного "зашифрован"
            indexFile = True

        for line in range(lines_count):
            _len = from_bytes(buf.read(4)) #Длина строки
            _len2 = from_bytes(buf.read(2)) #Она же еще раз?
            if _len != _len2:
                print("Некорректная длина в строке:", line)
            _str = buf.read(_len)

            if indexFile:
                _str = bytes([255-(i%5)-c for i,c in enumerate(_str)])

            result.append(_str.decode() + "\n") #Лучше чтобы все было сохранено в UTF-8

        _dir = os.path.dirname(txtfile)
        if not exists(_dir):
            os.mkdir(_dir)
            
        open(txtfile, 'wt').writelines(result)
         
    else:
        print('Некорректная длина файла', filename)
        
"""Функция кодирования текстового raw-файла"""
def encode_datafile(txtfile, zipfile, _encoding="cp1251"):

    lines = [line[:-1] for line in open(txtfile, 'rt').readlines()]
    buf = BytesIO()

    buf.write(from_int32(len(lines))) #Записываем количество строк

    file_path, fn = split(zipfile)
    indexFile = False
    if fn == 'index': #Файл index имеет туже структуру, но немного "зашифрован"
        indexFile = True

    for line in lines:
        line = line.encode(_encoding)
        _len = len(line)
        buf.write(from_int32(_len))
        buf.write(from_int16(_len))
        if indexFile:
            encoded = bytes([255-(i%5)-c for i,c in enumerate(line)])
            buf.write(encoded)
        else:
            buf.write(line)

    deflate = zlib.compress(buf.getvalue())
    buf.close()

    _dir = os.path.dirname(zipfile)
    if not exists(_dir):
        os.mkdir(_dir)

    _zip = open(zipfile, 'wb')
    _zip.write(from_int32(len(deflate)))
    _zip.write(deflate)
    _zip.close()


"""Функция рекурсивного обхода и декодирования файлов
Ищет файлы в каталоге data/ и сохраняет в data_src/"""
def decode_directory(frompath, topath):

    #Пробуем обрабатывать все файлы, у которых нет расширения
    for root, directories, files in os.walk(frompath):
        for file in files:
            fn, ext = splitext(file)
            if ext == "":
                new_path = root.replace(frompath, topath)
                decode_datafile(joinPath(root, file), joinPath(new_path, file) + ".txt")
            


def encode_directory(inputdir, outputdir):

    #Пробуем обрабатывать все файлы с расширением .txt
    for root, directories, files in os.walk(inputdir):
        for file in files:
            fn, ext = os.path.splitext(file) #Получаем имя файла без .txt
            if ext == ".txt":
                new_path = root.replace(inputdir, outputdir)
                encode_datafile(joinPath(root, file), joinPath(new_path, fn))
                
"""Функция загрузки файла с переводом в dict, указанный """
def load_dictionary(fn, strings_dict):
    import polib
    

def main():
    from optparse import OptionParser

    usage = "usage: %prog [options] src dst"

    parser = OptionParser(usage=usage)
    parser.add_option("-d", "--decode",
                      action="store_true", dest="action_decode",
                      default=False,
                      help="декодировать источник (файл или каталог)")
    
    parser.add_option("-e", "--encode",
                      action="store_true", dest="action_encode",
                      default=False,
                      help="закодировать источник (файл или каталог)")
    
    parser.add_option("-t", "--translate",
                      metavar="FILE", dest="dictionaryFile",
                      default=None,
                      help="переводить источник указанным файлом перевода (po/mo)")
    
    parser.add_option("-y", "--yes",
                      action="store_true", dest="rewrite",
                      default=False,
                      help="разрешить перезапись")

    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose",
                      default=False,
                      help="отображать процесс")

    (options, args) = parser.parse_args()
    
    if not options.action_decode and not options.action_encode:
        parser.print_help()
        parser.error("Необходимо выбрать метод (decode/encode)")
        
    if options.action_decode and options.action_encode:
        parser.print_help()
        parser.error("Необходимо выбрать только один из методов")
        
    if options.dictionaryFile !=None:
        if options.action_decode:
            if exists(options.dictionaryFile):
                TRASLATE_DICTIONARY = {}
                load_dictionary(options.dictionaryFile, TRASLATE_DICTIONARY)
                print(options.dictionaryFile)
            else:
                parser.error("Файл словаря %s не найден!" % options.dictionaryFile)
        else:
            parser.error("Перевод происходит ТОЛЬКО при декодировании")
    
    if len(args) != 2:
        parser.print_help()
        parser.error("Необходимо указать источник и направление")
    
    frompath = realpath(args[0])
    topath   = realpath(args[1])

    if exists(frompath):
        if isdir(frompath):
            #Если цель - каталог
            if exists(topath):
                if not options.rewrite:
                    answer = input("Каталог %s\nсуществует, перезаписать? [y/N] " % topath)
                    if not (answer in ["y","Y"]):
                        print("Прервано пользователем")
                        exit()
            
            #Обработка каталога, в зависимости от выбранного действия
            if options.action_decode:
                decode_directory(frompath, topath)
            elif options.action_encode:
                encode_directory(frompath, topath)
                
        elif isfile(frompath):
            #Если цель - один файл
            if exists(topath):
                if not options.rewrite:
                    answer = input("Файл %s\nсуществует, перезаписать? [y/N] " % topath)
                    if not (answer in ["y","Y"]):
                        print("Прервано пользователем")
                        exit()
                    
            #Обработка файла, в зависимости от выбранного действия
            if options.action_decode:
                decode_datafile(frompath, topath)
            elif options.action_encode:
                encode_datafile(frompath, topath)
        else:
            print("Не распознан тип файла")
    else:
        print("Заданный путь к источнику не существует")



if __name__ == '__main__':
    main()



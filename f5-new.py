import subprocess
import sys
import os
import csv
from ConfigParser import SafeConfigParser
from optparse import OptionParser
#from listaAlbero_app import listaAlbero,nomeStringA
#from listaVirtual import listaAlbero as listaVirtual,nomeStringV


class OID(object):
    def __init__(self):
        """
        costruttore, inizializza le variabili globali
        """
        self.listaOID = []      #salvo il risultato del subprocess
        self.normOID = {}       #dict di oid normalizzate prese con nnsnmpwalk
        self.daFileOID = {}     #dict di oid presi dal file di appoggio
        self.changeOID = {}     #dict di appoggio usata per sovrascrivere il file	
        self.oid = []		#lista di oid da controllare
        self.fqdn = []		#lista di fqdn da controllare

        self.mib_generale = '.1.3.6.1.4.1.9999.9999.200'
        self.mib_descrizione = '.1.3.6.1.4.1.9999.9999.200.1'
        self.mib_indice	 = '.1.3.6.1.4.1.9999.9999.200.2'
        self.mib_valore  = '.1.3.6.1.4.1.9999.9999.200.3'
        self.mib_soglia  = '.1.3.6.1.4.1.9999.9999.200.4'
        self.mib_stato 	 = '.1.3.6.1.4.1.9999.9999.200.5'
        self.mib_voce 	 = '.1.3.6.1.4.1.9999.9999.200.6'
        self.mib_testo	 = '.1.3.6.1.4.1.9999.9999.200.7'

        self.valoreSoglia = ''   #usata per il messaggio dello stato di uscita
        self.confronto = ['INTEGER','Unsigned32',]  #usata per normalizzare le mib con valore intero
        #self.listaAlbero = listaAlbero
        #self.listaVirtual = listaVirtual
        #self.nomeStringA = nomeStringA
        #self.nomeStringV = nomeStringV
        self.listaService = ''
        self.nomeStringa = ''

    def setConf(self,configFile):
        """
        legge il file di configurazione
            [GENERAL]
            OID=
            NAME=
            WARNING=
            CRITICAL=
            TMP_FILE=
            LIMITE=
            VOCE=
            TESTO=
            CUSTOM=          
        @param: nome file di configurazione
        """
        config = SafeConfigParser()
        config.read(configFile)

        #self.oid = config.get('GENERAL','OID')
        self.oid = self.checkMultiLIST(config.get('GENERAL','OID'))
        self.fqdn = config.get('GENERAL','FQDN')
        self.name = config.get('GENERAL','NAME')
        self.warning = config.get('GENERAL','WARNING')
        self.critical = config.get('GENERAL','CRITICAL')
        self.tmp_file = config.get('GENERAL','TMP_FILE')
        self.limite = config.get('GENERAL', 'LIMITE')
        self.voce = config.get('GENERAL', 'VOCE')
        self.testo = config.get('GENERAL', 'TESTO')

        if config.has_option('GENERAL','CUSTOM'):
            self.custom = config.get('GENERAL','CUSTOM')
        else:
            self.custom = ''

        if config.has_option('GENERAL','LISTA'):
            app = config.get('GENERAL','LISTA')
            self.listaService = app.split('\n')
        
        if config.has_option('GENERAL','NOMESTRINGA'):
           self.nomeStringa = config.get('GENERAL','NOMESTRINGA')    

    def getOID(self):
        """
        ottine il valore della oid, tramite nnmsnmpwalk.ovpl
        """
        try:
            for oid in self.oid:
                r = subprocess.Popen(['nnmsnmpwalk.ovpl',self.fqdn,oid], stdout=subprocess.PIPE)
                out = r.stdout.read()
                listaOID = out.split('\n')
                for l in listaOID:
                    self.listaOID.append(l)
                    #print(self.listaOID)
        except Exception as e:
            print("errore su nnmsnmpwalk.ovpl   --- {0}".format(e))

    def checkMultiLIST(self,l,c=','):
        """
        prende una stringa e la divinde dentro una lista
        @param l = stringa
        @param c = carattere speciale, valore di Default ','
        @return list
        """
        RES = []
        if l.find(','):
            l = l.split(',')
            for ll in l :
                RES.append(ll)
        else:
            RES.append(l)

        return RES

    ######## START SEND NNM ########
    def controlloSoglia(self,valore):
        """
            ########################################
            ####    controllare le varie soglie ####
            ########################################
            INVIO SOLO AL CAMBIO DI STATO
            RESET E ADD
            RES = 0 -- NORMAL
            RES = 1 -- WARNING
            RES = 2 -- CRITICAL
            RES = 3 -- UNKNOWN (testo)
        al cambio di stato viene inviato un valore di reset ed in seguito il nuovo stato
        @param valore = valore da controllare se in soglia oppure no
        @return : codici di soglia impostati
        """
        try:
            RES = ''
            v = str(valore).upper().strip()
            if v.find('OK') != -1:
                RES = 0
	    elif v.find('NORM') != -1:
                RES = 0
            elif v.find('WARN') != -1:
                RES = 1
            elif v.find('CRIT') != -1:
                RES = 2
            else:
                if int(self.limite) == 1:    #limite superiore
                    if int(valore) < int(self.warning):
                        RES = 0
                    elif int(valore) >= int(self.warning) and int(valore) < int(self.critical):
                        RES = 1
                    elif int(valore) >= int(self.critical):
                        RES = 2
                    else :
                        RES = 3
                elif int(self.limite) == 0: #valore inferiore
                    if int(valore) < int(self.critical):
                        RES = 2
                    elif int(valore) >= int(self.critical) and int(valore) <= int(self.warning):
                        RES = 1
                    elif int(valore) > int(self.warning) :
                        RES = 0
                    else :
                        RES = 3
                else:
                    RES = 3
            self.valoreSoglia = RES
            #print "RES: "+str(RES)
            return int(RES)
        except  ValueError as e:
            #print str(e)
            RES = 3
            return int(RES)

    def sendResetTrap(self,indice_oid,valore,stato_rilevato):
        """
        metodo per il reset della trap
        @param indice_oid 
        @param valore
        @param stato
        @param rilevato
        """
        #index
        #voce
        #stato = Reset
        #CMD = '/opt/OV/bin/nnmsnmpnotify.ovpl -v 2c "" -a {} {} {} {} {} {} {} {} {}'.format(self.fqdn, self.mib_generale, desc, index, value, soglia, stato, voce, testo)
        self.sendUpdateTrap(indice_oid,valore,stato_rilevato)

    def sendUpdateTrap(self,indice_oid,valore,stato_rilevato):
        """
        metodo generico di invio trap di aggiornamento
        fqdn = 		cdm-wf-lb01.ac.bankit.it
        generale =      .1.3.6.1.4.1.9999.9999.200
        descrizione = 	.1.3.6.1.4.1.9999.9999.200.1=sysChassisFanSpeed.3
        index =		.1.3.6.1.4.1.9999.9999.200.2=3
        value = 	.1.3.6.1.4.1.9999.9999.200.3=7142
        soglia = 	.1.3.6.1.4.1.9999.9999.200.4=4
        stato = 	.1.3.6.1.4.1.9999.9999.200.5=Normal
        voce  = 	.1.3.6.1.4.1.9999.9999.200.6=Voce
        testo  = 	.1.3.6.1.4.1.9999.9999.200.7=Testo
        @param indice_oid
        @param valore
        @param stato_rilevato
        """
	#print("sendUpdateTrap indice= {}, valore={}, stato={}".format(indice_oid,valore,stato_rilevato))
        desc = self.mib_descrizione +' octetstring "'+ str(indice_oid).strip()+'"'
        index = self.mib_indice
        stato = '""'
        if 'Load Balancing Pool' in str(indice_oid):
            s = str(valore).split('-')
            stato = self.mib_stato + ' octetstring "' + str(s[0]).strip()+'"'
            i = str(indice_oid).split('Pool')
            index = self.mib_indice + ' octetstring "' + str(i[1]).strip()+'"'

        elif 'Common' in str(indice_oid):
            index = self.mib_indice + ' octetstring "' + str(indice_oid).strip()+'"'
            s = str(valore).split('State:')
	    s = s[1].split(',')
            s = s[0].strip()
            if s.find('green') != -1:
                stato = self.mib_stato + ' octetstring "' + 'Normal"'
            else:
                stato = self.mib_stato + ' octetstring "' + 'Critical"'

	elif 'FileSystem' in str(indice_oid):
            vv = self.extractValueFileSystem(valore)
	    stato = self.mib_stato + ' octetstring "' + str(self.findStato(self.controlloSoglia(vv))).strip()+'"'

	elif 'CpuLoad' in str(indice_oid):
            vv = self.extractValueLoad(valore)
	    stato = self.mib_stato + ' octetstring "' + str(self.findStato(self.controlloSoglia(vv))).strip()+'"'

        else:
            index = self.mib_indice + ' octetstring "' + str(self.findIndex(indice_oid)).strip()+'"'
            stato = self.mib_stato + ' octetstring "' + str(self.findStato(stato_rilevato)).strip()+'"'


        value = self.mib_valore + ' octetstring "' + str(valore).strip()+'"'
        soglia = self.mib_soglia + ' octetstring "' + str(self.findValoreSoglia()).strip()+'"'
        voce = self.mib_voce + ' octetstring "' + str(self.voce).strip()+'"'
        #testo = self.mib_testo + ' octetstring "' +str(self.testo).strip()+' '+str(valore)+' (threshold '+str(self.findValoreSoglia()).strip()+')"'
        testo = self.mib_testo + ' octetstring "' + self.findTesto(valore,indice_oid,stato_rilevato) + '"'

        CMD = '/opt/OV/bin/nnmsnmpnotify.ovpl -v 2c "" -a {} {} {} {} {} {} {} {} {}'.format(self.fqdn, self.mib_generale, desc, index, value, soglia, stato, voce, testo)
        print CMD
        # ---INVIO TRAP--- #
        #r = subprocess.Popen([CMD],shell=True )# stdout=subprocess.PIPE,)
        #print r
    
    def findValoreSoglia(self):
        """
        trova la soglia da prendere in cosiderazione
        @return : ritorna il valore della soglia warning o critical da prendere in cosiderazione
        """
        ris = ''
        if self.valoreSoglia <= 1 :
            ris = self.warning
        elif self.valoreSoglia == 2 :
            ris = self.critical
        else :
            pass

        return ris

    def findIndex(self,key):
        """
        trova l'indice per la trap di uscita 	sysChassisTempTemperature.6
        @param key: chiave contenente l'indice
        @return : valore numerico dell 'indice
        """
        #print key
        index = key.split('.')
        return index[1]

    def findStato(self,valore_rilevato):
        """
        trova lo stato dell'errore
        0 = NORMAL
        1 = WARNING
        2 = CRITICAL
        3 = UNKNOWN
        @param valore_rilevato
        @return : tipo di stato
        """
        ris = ''
        #if self.valoreSoglia == 0 :
        #print valore_rilevato
        if valore_rilevato == 0 :
            ris = 'Normal'
        #elif self.valoreSoglia == 1:
        elif valore_rilevato == 1:
            ris = 'Warning'
        #elif self.valoreSoglia == 2:
        elif valore_rilevato == 2:
            ris = 'Critical'
        else :
            ris = 'UNKNOWN'
        return ris

    def findTesto(self,valore,indice_oid,stato_rilevato=''):
	"""
        @param valore
        @param indice_oid
        @param stato_rilevto

	chiavi da inserire per cambiare il messaggio
	__VALORE__     --> valore rilevato
	__FINDVALORESOGLIA__   --> valore soglia
	__NODO__	--> ip del nodo
	__INDEX__	--> indice
	__STATO__	--> stato allarme 
        __TIPO__        --> 
        -----usati per la memoria---
        __PERCENTO__    --> valore in percento
        __USATA__       --> memoria usata
        __TOTALE__      --> memoria totale
	"""
        #app = v[1]+','+str(stato)+','+appUsed[k]+','+appSize[k]+','+str(perc).strip()+'%'
        #OK - 17.1% used (516.09 MB of 2.95 GB), (levels at 80.00/90.00%), trend: +364.23 kB / 24 hours
        res = ''
        #if self.testo.find('FileSystem') != -1:
        if valore.find('FileSystem') != -1:
            app = valore.split(',') 
            res = self.testo.replace('__FS__', str(app[0]))
            #res = res.replace('__STATO__', app[1].strip())
            res = res.replace('__PERCENTO__', app[3].strip())
            res = res.replace('__USATA__', app[1].strip())
            res = res.replace('__TOTALE__', app[2].strip())
            res = res.replace('__FINDVALORESOGLIA__', self.findValoreSoglia().strip())

        elif indice_oid.find('ssCpu') != -1:
            tipo = indice_oid.split('Cpu')
            res = self.testo.replace('__TIPO__',tipo[1])
            #res = res.replace('__STATO__', str(stato_rilevato).strip())
            #res = res.replace('__VALORE__', self.findValoreSoglia().strip())+'%'
            res = res.replace('__VALORE__', str(valore)+'%')
            res = res.replace('__FINDVALORESOGLIA__', self.findValoreSoglia().strip())+'%)'

        elif indice_oid.find('CpuLoad') != -1:
             res = self.testo.replace('__VALORE__', str(valore))
             #s = str(valore).split('is at')
             #v = float(s[1].strip())
             #vv = int(v)
             vv = self.extractValueLoad(valore)
             self.controlloSoglia(str(vv))
             res = res.replace('__FINDVALORESOGLIALOAD__', self.findValoreSoglia()).strip()
        else:
            res = self.testo.replace('__VALORE__', str(valore))
            res = res.replace('__FINDVALORESOGLIA__', self.findValoreSoglia().strip())
            res = res.replace('__NODO__', str(self.fqdn))
            if res.find('__INDEX__') != -1:
                res = res.replace('__INDEX__', str(self.findIndex(indice_oid)).strip())
	    res = res.replace('__STATO__', str(self.findStato(stato_rilevato)).strip())

        return res


    def sendListaNNM(self,nnM):
        """
        metodo di appoggio per l'invio delle trap, da una lista-di-liste estrae i valori da inviare
        @param nnM: list-of-list
        """
        for n in nnM:
            if len(n) == 3:
                self.sendNNM(n[0],n[1],n[2])
            else:
                self.sendNNM(n[0],n[1])

    def sendNNM(self,indice_oid,valore,oldValore=False):
        """
        CONDIZIONI DI INVIO TRAP AD NNM
        1- oldValore == False  --> significa che e' la prima volta che viene eseguita, viene inviata la trap di notifica
        2- Valore == valore --> significa che non c'e' stato nessun cambio di stato, la trap NON viene inviata
        3- oldValore != valore
                        |_____eseguo il controllo di soglia_____
                        |
                        |_3.1 CAMBIO DI STATO  --> invio la trap di reset e la trap di aggiornamento <diveso>
                        |_3.2 NESSUN CAMBIO DI STATO NON INVIO LA TRAP                          <uguale>


        /opt/OV/bin/nnmsnmpnotify.ovpl -v 2c FQDN <NOMECONTROLLO> SOGLIA VALORE OID

        @param indice_oid: <str>    indice della oid
        @paran valore: <str>    valore acqiosito dalla trap
        @param oldValore: <str> valore acquisito dal file 
        """
        #print("sendNNM")
        if not oldValore :							#condizione 1
            status = self.controlloSoglia(valore)
            self.sendUpdateTrap(indice_oid,valore,oldValore)
        elif valore == oldValore :					#condizione 2
            pass
        else :
            oldStatus = self.controlloSoglia(oldValore)
            newStatus = self.controlloSoglia(valore)

            #print('controllo uguali {} {}'.format(oldStatus,newStatus))				#condizione 3
            if oldStatus != newStatus:		 				#condizione 3.1
                self.sendResetTrap(indice_oid,oldValore,oldStatus)
                self.sendUpdateTrap(indice_oid,valore,newStatus)

            elif oldStatus == 3 and newStatus == 3:			#sono nella condizione di avere una mib di carattere descrittivo
                #### ADD controllo per MIB descrittiva ####
                #print("DDDDD")
                if self.controlloStatusUnknow(oldValore,valore):
                    self.sendResetTrap(indice_oid,oldValore,oldStatus)
                    self.sendUpdateTrap(indice_oid,valore,newStatus)
            else:							#condzione 3.2
                #print("non invio nulla")
                pass

    def controlloStatusUnknow(self,old_valore,valore):
        """
        nel caso di trap con valore testo non numerico effetto un controllo personalizzato
        @param old_valore
        @param valore
        @return status True/False
        """
        RIS = True
        OLD = ''
        NEW = ''
        if valore.find('is at') > 0 and old_valore.find('is at') > 0:
            OLD = self.controlloSoglia(self.extractValueLoad(old_valore))
            NEW = self.controlloSoglia(self.extractValueLoad(valore))
            print('old {0} type {1}, new {2} type {3}'.format(OLD,type(OLD),NEW,type(NEW)))
            if OLD == NEW :
                RIS = False
        elif valore.find('FileSystem:') > 0 and old_valore.find('FileSystem:') > 0:
            OLD = self.controlloSoglia(self.extractValueFileSystem(old_valore))
            NEW = self.controlloSoglia(self.extractValueFileSystem(valore))
            if OLD == NEW :
                RIS = False
        return RIS

    ######## END SEND NNM ########
    
    ######## START UTILITY ########
    def extractValueLoad(self,valore):
        """
        estraggo il valore dalla Load
        @param valore
        @return valore da controllare
        """
        RIS=3
        if valore.find('is at') != -1 :
            s = str(valore).split('is at')
            v = float(s[1].strip())
            RIS = int(v)

        return str(RIS)

    def extractValueFileSystem(self,valore):
        """
        estraggo il valore per il filesystem
        @param valore
        @return valore da controllare
        """
        RIS=3
        if valore.find('FileSystem:') != -1 :
            s = valore.split(',')
            RIS = s[3][:-1].strip()
	
        return RIS
    ######## END UTILITY ########

    ####### START NORMALIZZA OID #######
    def normalOID(self):
        """
        normalizza la oid presa da nnmsnmpnotify.ovpl
        """
        for l in self.listaOID:
            #if 'Index' not in l:
                if len(l) !=0:
                    if l.find(self.name) > 0:
                        s=l.split(self.name)
                        l=s[1].split(':')
                        ll=s[1]
                        value=ll[ll.index(':')+1:]
                        #self.normOID[l[0][1:]]=l[len(l)-1]
                        self.normOID[l[0][1:]]=self.normalVALUE(value)
                    else:
                        ll = l
                        l=l.split(':')
                        value=ll[ll.index(':')+1:]
                        #self.normOID[l[0]]=l[len(l)-1]
                        self.normOID[l[0]]=self.normalVALUE(value)

    def normalVALUE(self,value):
        """
        converte in valori numerici le stringe che contengono INTEGER, Unsigned32
        """
        res = value
        for f in self.confronto:
            if value.find(f) >= 0 :
                r = value.split(':')
                res = r[1]
        return res

    ####### END NORMALIZZA OID #######

    def checkDiff(self):
        """
        controlla nel file di tmp il vecchio valore
        {'sysChassisTempTemperature.1 ':' 25'}
                ####	AGGIUNGERE FQDN   ####
        """
        nnM=[]  # indice_oid,valore,oldValore=False)   --- DA AGGIUNGERE FQDN

        writeF=False
        sendTrap=False
        if os.path.isfile(self.tmp_file):
            #print("il file esiste")
            #se il file esiste eseguo l'import
            f = open(self.tmp_file,'r')
            for line in f:
                l=line.replace("\n","")
                l=l.split(';')
                self.daFileOID[l[0]]=l[1]
            f.close()
            for k,v in self.normOID.iteritems():
                if self.daFileOID.has_key(k):   # la chiave e' presente sul file di appoggio
                                                        # confronto i valori
                    #print 'k'+k+'-F-'+self.daFileOID[k]+'-N-'+self.normOID[k]+'-'
                    if self.daFileOID[k] != self.normOID[k]:        # i valori sono differenti
                        #print 'k'+k+'-F-'+self.daFileOID[k]+'-N-'+self.normOID[k]+'-'
                        # aggiounogo k v su un dict di appoggio presa da normOID
                        self.changeOIDFile(k,v)
                        nnM.append([k,v,self.daFileOID[k]])  #k k chiave, v valore nuovo, self.daFileOID valore vecchio
                        #print nnM
                        #self.sendNNM(k,v,self.daFileOID[k])
                        writeF=True

                    else :  # i valori sono uguali, li aggiungo alla dict per costruire il file
                        # aggiungo k v su un dict di appoggio presa da normOID
                        self.changeOIDFile(k,v)

                else:   # la chiave non risulta sul file di appoggio
                    # aggiounogo k v su un dict di appoggio presa da normOID
                    #print '#'+str(self.daFileOID[k])+'#'+str(self.normOID[k])+'#'
                    self.changeOIDFile(k,v)
                    nnM.append([k,v])
                    self.sendNNM(k,v)
                    writeF=True

            if writeF:
                self.writeFile(self.changeOID)
                self.sendListaNNM(nnM)
                #print("eseguo l'update del file")
            #else:
                #print("nessun cambiamento da apportare")

        else:
            ######################
            # IL FILE NON ESISTE #
            #####################
            #print("scrivo il file")
            self.writeFile(self.normOID)  #scrivo sul file per vedere le differenze con il prossimo controllo
            #for k,v in self.normOID.iteritems():
                #self.sendNNM(k,v)

    def changeOIDFile(self,k,v):
        """
        crea un dict che sovrascrive i file creato in precedenza
        @param k: oid
        @param v: value
        """
        self.changeOID[k]=v

    ####### START CUSTOM ATTRIBUTE ##########
    def memoriUsata(self):
        """
        esegue due entry e calcola la memoria utilizzata
        """
        hrStorageSize = {}
        hrStorageUsed = {}
        percento={}
        for k,v in self.normOID.iteritems():
            #print k
            l= k.split('.')
            #print l
            if l[0].find('hrStorageSize') >= 0:
                hrStorageSize[l[1]] = v
            elif l[0].find('hrStorageUsed') >= 0:
                hrStorageUsed[l[1]] = v
            else:
                pass

        for index_used,value_used in hrStorageUsed.iteritems():
            c = (float(value_used) / float(hrStorageSize[index_used])) * 100
            newKey = "hrStorage."+str(index_used)
            #percento[newKey] = str(int(c))+" %"
            percento[newKey] = str(int(c))

        #for	 k,v in percento.iteritems():
            #print k, v

        return percento
    
    def associazioneOID(self,listaCommon,nomeString):
        """
        """
        mib = ''
        lista = {}
        for k,v in self.normOID.iteritems():
            #for la in self.listaAlbero:    #parte 1
            for la in listaCommon:    #parte 1
                if la in v:
                    for oid in self.oid:
                        if oid in k:
                            oid = k.split(oid)
                            mib = oid[1][1:]   #trovo la mib da confrontare con altre
                            mib=mib.strip()
                            if self.custom.upper().strip() == 'ALBERO':
                                key,value=self.associazioneOID_NUM(mib,la,nomeString)
                            elif self.custom.upper().strip() == 'VIRTUAL':
                                key, value = self.virtualServer(mib, la, nomeString)
                            lista[key]=value

        return lista   #dict
 
    def associazioneOID_NUM(self, mib, nomeAlbero, nomeString):
        """
        in base alla mib trovata effettuo l'associazione
        @param mib:
        @return : key,value
        """
        key=''
        value=''
        contatore = 0
        OK_ = 0
        ERR_ = 0
        NOMI_NODO = ''
        for k,v in self.normOID.iteritems():
            if mib in k :
                if not('STRING' in v):
                    contatore = contatore + 1
                    if int(v) < 5 :
                        OK_ = OK_ + 1
                    else:
                        ERR_ = ERR_ + 1
                else:
                    if not(nomeAlbero in v):
                        app = v.split(':')
                        NOMI_NODO = NOMI_NODO + app[1]+','

        #key = self.nomeString + ' ' +nomeAlbero
        key = nomeString + ' ' +nomeAlbero

        if OK_ > 0 and ERR_ <= 0 :
            value = "Normal - {} of {} members are up".format(OK_,contatore)
        else:
            value = "Critical - {} of {} members are up, down/disabled nodes {}".format(OK_,contatore,OK_,NOMI_NODO)

        return 	key,value

    def virtual(self,listaCommon,nomeString):
	"""
	"""
        mib = ''
        lista = {}
        listaErr={0:'none', 1:'green', 2:'yellow', 3:'red', 4:'blue', 5:'gray'}
        virtualName = {}
        virtualAvailState = {}
        virtualClientTotConns = {}
        virtualClientCurConns = {}
        for k,v in self.normOID.iteritems():
            if k.find('ltmVirtualServName') != -1 :
                k = k.split('ltmVirtualServName.')
		k = k[1]
                v = v.split(':')
                virtualName[k]=v[1]
            elif k.find('ltmVsStatusAvailState') != -1 :
                k = k.split('ltmVsStatusAvailState.')
                k = k[1]
                virtualAvailState[k]=v
            elif k.find('ltmVirtualServStatClientTotConns') != -1 :
                k = k.split('ltmVirtualServStatClientTotConns.')
                k = k[1]
                v = v.split(':')
                virtualClientTotConns[k]=v[1]
            elif k.find('ltmVirtualServStatClientCurConns') != -1 :
                k = k.split('ltmVirtualServStatClientCurConns.')
                k = k[1]
                virtualClientCurConns[k]=v

        for k,v in virtualName.iteritems():
            for ll in listaCommon:
                print "virutual "+ ll
                if ll.strip().find(v.strip()) != -1:
                    lista[v] = v+', State: '+listaErr[int(virtualAvailState[k])]+', ClientTotConns: '+virtualClientTotConns[k]+', ClinetCurConns: '+virtualClientCurConns[k]    
                    #lista[k] = v+', '+listaErr[int(virtualAvailState[k])]+', '+virtualClientTotConns[k]+' ,'+virtualClientCurConns[k]    

        return lista

    def chassisFan(self):
        """
        metodo custom per l'analisi e la presentazione delle ventole dello chassis
        """
        statoD = {1: 'Ok', 2: 'Warning', 3: 'Critical'}
        msgI = 'Fan Processor.'
        appS={}
        appF={}
        res={}
        for k,v in self.normOID.iteritems():
            if k.find("sysChassisFanStatus") != -1:
                k = k.split('.')
                k = int(k[1])
                appS[k] = v
            elif k.find("sysChassisFanSpeed") != -1:
                k = k.split('.')
                k = int(k[1])
                appF[k] = v

        #FAN Processor 1 OK - speed is 9574 rpm
        for k,v in appS.iteritems():
            i = msgI+str(k)
            #msg = "{} - speed is {} rpm".format(statoD[int(v)].upper(),appF[k])
            msg = "{}".format(appF[k])
            #msg = appF[k]  #scrivo solo il numero
            res[i] = msg

        return res

    def chassisTemp(self):
        """
        metodo custom per l'analisi e la presentazione delle temperatura dello chassis
        """
        #Temperature Chassis 1  OK - 25 C
        msgT = 'Temperature Chassis.'
        appS={}
        appF={}
        res={}
	#print self.normOID
        for k,v in self.normOID.iteritems():
            if k.find("sysChassisTempIndex") != -1:
                k = k.split('.')
                k = int(k[1])
                appS[k] = v
            elif k.find("sysChassisTempTemperature") != -1:
                k = k.split('.')
                k = int(k[1])
                appF[k] = v

        for k,v in appS.iteritems():
            i = msgT+str(k)
            #msg = "{} - {}".format(statoD[int(v)].upper(),appF[k])
            msg = appF[k]
            res[i] = msg
        return res

    def cpu(self):
	return self.normOID

    def cpuLoad(self):
        msg = 'CpuLoad.'
        laLoad={}
        laIndex={}
        laNames={}
        res={}
        for k,v in self.normOID.iteritems():
            if k.find("laIndex") != -1:
                k = k.split('.')
                k = int(k[1])
                laIndex[k]=v
            elif k.find("laLoad") != -1:
                k = k.split('.')
                k = int(k[1])
                if v.find(":") != -1:
                    v = v.split(':')
                    v = v[1]
                laLoad[k] = v
            elif k.find("laNames") != -1:
                k = k.split('.')
                k = int(k[1])
                if v.find(":") != -1:
                    v = v.split(':')
                    v = v[1]
                laNames[k] = v

        for k,v in laIndex.iteritems():
            i = msg+str(k)
            value=str(laNames[k])+' is at '+str(laLoad[k])
            res[i] = value

	return res #self.normOID

    def fileSystem(self):
	return self.normOID

    def interface(self):
	return self.normOID

    def storage(self):
        """
        metodo custom per l'analisi e la presentazione dello storage
        """
	appDesc = {}
	appUsed = {}
	appSize = {}
	appUnit = {}
	for k,v in self.normOID.iteritems():
	    if k.find("hrStorageDescr") != -1:
		k = k.split('.')
		#k = 'index.'+k[1]
		k = 'FileSystem.'+k[1]
		appDesc[k]=v

	    elif k.find("hrStorageSize") != -1:
		k = k.split('.')
		#k = 'index.'+k[1]
		k = 'FileSystem.'+k[1]
		appSize[k]=v

            elif k.find("hrStorageUsed") != -1:
                k = k.split('.')
		#k = 'index.'+k[1]
		k = 'FileSystem.'+k[1]
                appUsed[k]=v

            elif k.find("hrStorageAllocationUnits") != -1:
                k = k.split('.')
                #k = 'index.'+k[1]
		k = 'FileSystem.'+k[1]
                appUnit[k]=v

	for k,v in appDesc.iteritems():
		c = (float(appUsed[k]) / float(appSize[k])) * 100
		perc = int(c)	

		v = v.split(':')
		stato = self.findStato(self.controlloSoglia(perc))
                usata = float(appUsed[k])*float(appUnit[k])
		usata = float(usata/(1024**2))
		usata = "%.2f" % usata
		size = float(appSize[k])*float(appUnit[k])
		size = float(size/(1024**3))
		size = "%.2f" % size
                
                #      FileSystem: /var ,Used: 597.36 ,Size: 2.95, 19%,  4096
		app = 'FileSystem:'+v[1]+' ,Used: '+str(usata)+' ,Size: '+str(size)+', '+str(perc).strip()+'%, '+appUnit[k]
		#app = v[1]+', '+str(stato)+', '+str(usata)+', '+str(size)+', '+str(perc).strip()+'% , '+appUnit[k]
		appDesc[k]=app

        return appDesc



    ####### END CUSTOM ATTRIBUTE ##########

    def run(self):
        """
        elenco dei controlli da eseguire
        -se per ragioni di sviluppo si vuole eseguire l'applicazione senza interrogare l'host remoto, 

        """
        self.getOID()
        self.normalOID()
        #self.toCSV()
        #self.fromCSV()
        self.customLauncher(self.custom)
        self.checkDiff()
        for k,v in self.normOID.iteritems():
                print(k,v)

    def customLauncher(self,custom=None):
        """
        launcher persnalizzato per alcuni controlli specifici
        @param custom, il valore viene preso dal file di configurazione, se presente, per Default None
        """
        if custom.upper().strip() == 'ALBERO':    #ok
            self.normOID = self.associazioneOID(self.listaService, self.nomeStringa)
        elif custom.upper().strip() == 'VIRTUAL':    #ok
            #self.normOID = self.virtual(self.listaVirtual, self.nomeStringV)
            self.normOID = self.virtual(self.listaService, self.nomeStringa)
        elif custom.upper().strip() == 'MEMORIA':    #ok
            self.normOID = self.memoriUsata()    
        elif custom.upper().strip() == 'FAN':    #ok
            self.normOID = self.chassisFan()
        elif custom.upper().strip() == 'TEMP':    #ok
            self.normOID = self.chassisTemp()
        elif custom.upper().strip() == 'FILESYSTEM':
            self.normOID = self.fileSystem()
        elif custom.upper().strip() == 'INTERFACE':
            self.normOID = self.interface()
        elif custom.upper().strip() == 'CPU':    #ok
            self.normOID = self.cpu()
        elif custom.upper().strip() == 'CPULOAD':    
            self.normOID = self.cpuLoad()
        elif custom.upper().strip() == 'STORAGE':    #ok
            self.normOID = self.storage()
        else:
            pass

    def writeFile(self,normOID):
        """
        scritture sul file
        @param: normOID
        fqdn; oid ;valore
        [ { 'FQDN': fqdn, 'OID': oid, 'VALUE':value}, ]
        """
        f=open(self.tmp_file,'w')
        for k,v in normOID.iteritems():
            f.write(k+";"+v+"\n")
        f.close()

    def toCSV(self,fileName='file.csv'):
        """
        create csv to dict, archivi nel file il risultato ottenuto da getOID
        @param fileName
        """
        #fileName="dirname_cpu.csv"
        with open(fileName,'wb') as f:
            w = csv.DictWriter(f, self.normOID.keys())
            w.writeheader()
            w.writerow(self.normOID)

    def fromCSV(self,fileName='dirname_storage.csv'):
        """
        evita di dover fare una connessione di volta in volta per velocizzare la fase di creazione dei moduli
        @param fileName
        """
        reader = csv.DictReader(open(fileName, 'rb'))
        dict_list = []
        for line in reader:
            dict_list.append(line)
            #print("{} len".format(len(line)))

        for k,v in dict_list[0].iteritems():
	    #print("K= {} V= {}".format(k,v))
            self.normOID[k]=v
	

if __name__ == '__main__':
    """
    example ./f5-plugin.py -f FILECONF
    """
    if sys.argv > 1:
        fileConf = sys.argv[1]

        oid = OID()
        oid.setConf(fileConf)
        oid.run()
    else :
	print("ERRORE parametri di avvio mancanti")

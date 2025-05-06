import logging
from time import sleep
import time
from typing import List, Tuple
import math

import numpy as np
from scipy.signal import savgol_filter
from scipy.signal import medfilt
from scipy import ndimage

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSlot, pyqtSignal

from NanoVNASaver.Calibration import correct_delay
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Settings.Sweep import Sweep, SweepMode
from NanoVNASaver.Touchstone import Touchstone

logger = logging.getLogger(__name__)

def truncate(values: List[List[Tuple]], count: int) -> List[List[Tuple]]:
    """truncate drops extrema from data list if averaging is active"""
    keep = len(values) - count
    logger.debug("Truncating from %d values to %d", len(values), keep)
    if count < 1 or keep < 1:
        logger.info("Not doing illegal truncate")
        return values
    truncated = []
    for valueset in np.swapaxes(values, 0, 1).tolist():
        avg = complex(*np.average(valueset, 0))
        truncated.append(
            sorted(valueset,
                   key=lambda v, a=avg:
                   abs(a - complex(*v)))[:keep])
    return np.swapaxes(truncated, 0, 1).tolist()

class WorkerSignals(QtCore.QObject):
    updated = pyqtSignal()
    finished = pyqtSignal()
    sweepError = pyqtSignal()
    calcnow = pyqtSignal()


class SweepWorker(QtCore.QRunnable):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        logger.info("Initializing SweepWorker")
        self.signals = WorkerSignals()
        self.app = app
        self.sweep = Sweep()
        self.setAutoDelete(False)
        self.percentage = 0
        self.data11: List[Datapoint] = []
        self.data21: List[Datapoint] = []
        self.rawData11: List[Datapoint] = []
        self.rawData21: List[Datapoint] = []
        self.init_data()
        self.stopped = False
        self.running = False
        self.error_message = ""
        self.offsetDelay = 0
        self.time_sweep = 0.0

        #Parametros de escritura Continua

        #Vector de Resonancia : Hz - dB - Ph
        self.fr: List[float] = []
        self.mg: List[float] = []
        self.dg: List[float] = []

        #Vector de datapoints S21 - Tiempos de barrido - Contador de Sweeps
        self.alls21:List[List[Datapoint]] = []
        self.alls11: List[List[Datapoint]] = []
        self.tm: List[float] = []
        self.inic = 0
        #Valores Actuales de F-dB-Ph-t

        self.actfr = 0
        self.actf = 0
        self.actg = 0
        self.actm = 0

        self.actt = 0
        self.actdp = 0

        self.pi = math.pi

    @pyqtSlot()
    def run(self) -> None:
        try:
            self._run()
        except BaseException as exc:  # pylint: disable=broad-except
            logger.exception("%s", exc)
            self.gui_error(f"ERROR during sweep\n\nStopped\n\n{exc}")
            if logger.isEnabledFor(logging.DEBUG):
                raise exc

    def _run(self) -> None:
        logger.info("Initializing SweepWorker")
        if not self.app.vna.connected():
            logger.debug(
                "Attempted to run without being connected to the NanoVNA")
            self.running = False
            return

        self.running = True
        self.percentage = 0

        with self.app.sweep.lock:
            sweep = self.app.sweep.copy()

        if sweep != self.sweep:  # parameters changed
            self.sweep = sweep
            self.init_data()

        self._run_loop()

        if sweep.segments > 1:
            start = sweep.start
            end = sweep.end
            logger.debug("Resetting NanoVNA sweep to full range: %d to %d",
                         start, end)
            self.app.vna.resetSweep(start, end)

        self.percentage = 100
        logger.debug('Sending "finished" signal')
        self.signals.finished.emit()
        self.running = False

    def _run_loop(self) -> None:

        sweep = self.sweep
        averages = (sweep.properties.averages[0]
                    if sweep.properties.mode == SweepMode.AVERAGE
                    else 1)
        logger.info("%d averages", averages)

        self.nstop = sweep.properties.nsweeps
        self.inic = 0
        self.ttr=0
        self.alls11.clear()
        self.alls21.clear()
        self.tm.clear()

        filename='D:/Usuario Martin/Escritorio/Experimentos/Exps/Barrido.s2p'

        #print(self.app.vna.datapoints)

        cantseg = 0
        multcantseg = 1

        if sweep.segments <=4 :
            cantseg = 1
        else :
            cantseg = sweep.segments

        while True:

            t_st = time.time()

            for i in range(sweep.segments):
                logger.debug("Sweep segment no %d", i)

                #Interrupción Stop
                if self.stopped:
                    logger.debug("Stopping sweeping as signalled")
                    break
                    ############

                start, stop = sweep.get_index_range(i)
                #print(sweep.get_index_range(i))

                freq, values11, values21 = self.readAveragedSegment(start, stop, averages)

                self.percentage = (i + 1) * 100 / sweep.segments

                #ETAPA DE FILTRADO
                # Extraer las columnas
                columna_1 = [fila[0] for fila in values21]
                columna_2 = [fila[1] for fila in values21]

                # Aplicar el filtro Savitzky-Golay a cada columna
                columna_1_filtrada = savgol_filter(columna_1, window_length=11, polyorder=2)
                columna_2_filtrada = savgol_filter(columna_2, window_length=11, polyorder=2)

                # Recomponer la matriz filtrada (opcional)
                values21 = [[columna_1_filtrada[i], columna_2_filtrada[i]] for i in range(len(columna_1_filtrada))]

                # Supongamos que `signal` es tu lista de datos y `frequencies` es la lista de frecuencias correspondientes
                #frequencies = np.array(freq)  # lista de frecuencias
                #signal = np.array(values21)  # lista de señales

                # Aplicar un filtro de mediana
                #window_size = 201  # Tamaño de la ventana
                #baseline = ndimage.median_filter(signal, window_size)

                #baseline = medfilt(signal, window_size)

                # Corregir la señal
                #corrected_signal = signal - baseline
                #values21 = corrected_signal.tolist()


                self.updateData(freq, values11, values21, i)

                #print(self.data21[i])


            #Condicional de Barrido Simple / Continuo
            self.inic = self.inic+1

            s11 = self.data11
            self.alls11.append(s11)

            s21 = self.data21
            self.alls21.append(s21)


            if sweep.properties.mode == SweepMode.SINGLE:

                if sweep.properties.anmode == 0: #Analizar

                    mg = -100
                    cont = 0


                    for i in s21:
                        if i.gain > mg:
                            #if -0.5 < i.phase * (180 / 3.14) < 0.5:
                                self.actm = i.gain
                                self.actf = i.freq
                                self.actg = i.phase * (180 / self.pi)
                                self.actfr = cont
                                mg = i.gain
                        cont = cont + 1

                    self.mg.append(self.actm)
                    self.fr.append(self.actf)
                    self.dg.append(self.actg)

                if sweep.properties.anmode == 1:

                    self.actm = s21[self.actfr].gain
                    self.actf = s21[self.actfr].freq
                    self.actg = s21[self.actfr].phase * (180 / self.pi)

                    self.mg.append(self.actm)
                    self.fr.append(self.actf)
                    self.dg.append(self.actg)

                tact = time.time()
                self.actt = round(tact - t_st, 2)

                self.ttr = round(self.ttr + self.actt, 2)
                self.tm.append(self.ttr)

                self.signals.calcnow.emit()
                break

            if sweep.properties.mode == SweepMode.CONTINOUS:

                if sweep.properties.anmode == 0 :

                    mg = -100
                    cont = 0

                    for i in s21:
                        if i.gain > mg:
                            if -0.1 < i.phase* (180 / self.pi) < 0.1:
                                self.actm = i.gain
                                self.actf = i.freq
                                self.actg = i.phase * (180 / self.pi)
                                self.actfr = cont
                                mg = i.gain
                        cont=cont+1

                    self.mg.append(self.actm)
                    self.fr.append(self.actf)
                    self.dg.append(self.actg)

                if sweep.properties.anmode == 1:

                    self.actm = s21[self.actfr].gain
                    self.actf = s21[self.actfr].freq
                    self.actg = s21[self.actfr].phase * (180/self.pi)

                    self.mg.append(self.actm)
                    self.fr.append(self.actf)
                    self.dg.append(self.actg)

                tact = time.time()
                self.actt = round(tact - t_st, 2)

                self.ttr = round (self.ttr + self.actt , 2)
                self.tm.append(self.ttr)


                letra='x'
                posf = filename.rfind('B')
                faux = filename[:posf] + str(self.inic) + letra + filename[posf:]
                ts = Touchstone(faux)
                ts.sdata[0] = s11
                ts.sdata[1] = s21
                for dp in s11:
                    ts.sdata[2].append(Datapoint(dp.freq, 0, 0))
                    ts.sdata[3].append(Datapoint(dp.freq, 0, 0))
                ts.save(4)

                self.signals.calcnow.emit()

            if self.inic == self.nstop:
                break


    def init_data(self):
        self.data11 = []
        self.data21 = []
        self.rawData11 = []
        self.rawData21 = []
        for freq in self.sweep.get_frequencies():
            self.data11.append(Datapoint(freq, 0.0, 0.0))
            self.data21.append(Datapoint(freq, 0.0, 0.0))
            self.rawData11.append(Datapoint(freq, 0.0, 0.0))
            self.rawData21.append(Datapoint(freq, 0.0, 0.0))
        logger.debug("Init data length: %s", len(self.data11))

    def updateData(self, frequencies, values11, values21, index):
        # Update the data from (i*101) to (i+1)*101
        logger.debug(
            "Calculating data and inserting in existing data at index %d",
            index)
        offset = self.sweep.points * index

        raw_data11 = [Datapoint(freq, values11[i][0], values11[i][1])
                      for i, freq in enumerate(frequencies)]
        raw_data21 = [Datapoint(freq, values21[i][0], values21[i][1])
                      for i, freq in enumerate(frequencies)]

        data11, data21 = self.applyCalibration(raw_data11, raw_data21)
        logger.debug("update Freqs: %s, Offset: %s", len(frequencies), offset)
        for i in range(len(frequencies)):
            self.data11[offset + i] = data11[i]
            self.data21[offset + i] = data21[i]
            self.rawData11[offset + i] = raw_data11[i]
            self.rawData21[offset + i] = raw_data21[i]

        logger.debug("Saving data to application (%d and %d points)",
                     len(self.data11), len(self.data21))
        self.app.saveData(self.data11, self.data21)
        logger.debug('Sending "updated" signal')
        self.signals.updated.emit()

    def applyCalibration(self,
                         raw_data11: List[Datapoint],
                         raw_data21: List[Datapoint]
                         ) -> Tuple[List[Datapoint], List[Datapoint]]:
        data11: List[Datapoint] = []
        data21: List[Datapoint] = []

        if not self.app.calibration.isCalculated:
            data11 = raw_data11.copy()
            data21 = raw_data21.copy()
        elif self.app.calibration.isValid1Port():
            data11.extend(self.app.calibration.correct11(dp)
                          for dp in raw_data11)
        else:
            data11 = raw_data11.copy()

        if self.app.calibration.isValid2Port():
            for counter, dp in enumerate(raw_data21):
                dp11 = raw_data11[counter]
                data21.append(self.app.calibration.correct21(dp, dp11))
        else:
            data21 = raw_data21

        if self.offsetDelay != 0:
            data11 = [correct_delay(dp, self.offsetDelay, reflect=True)
                      for dp in data11]
            data21 = [correct_delay(dp, self.offsetDelay) for dp in data21]

        return data11, data21

    def readAveragedSegment(self, start, stop, averages=1):
        values11 = []
        values21 = []
        freq = []
        logger.info("Reading from %d to %d. Averaging %d values",
                    start, stop, averages)
        for i in range(averages):
            if self.stopped:
                logger.debug("Stopping averaging as signalled.")
                if averages == 1:
                    break
                logger.warning("Stop during average. Discarding sweep result.")
                return [], [], []
            logger.debug("Reading average no %d / %d", i + 1, averages)
            retry = 0
            tmp11 = []
            tmp21 = []
            while not tmp11 and retry < 5:
                sleep(0.5 * retry)
                retry += 1
                freq, tmp11, tmp21 = self.readSegment(start, stop)
                if retry > 1:
                    logger.error("retry %s readSegment(%s,%s)",
                                 retry, start, stop)
                    sleep(0.5)
            values11.append(tmp11)
            values21.append(tmp21)
            self.percentage += 100 / (self.sweep.segments * averages)
            self.signals.updated.emit()

        if not values11:
            raise IOError("Invalid data during swwep")

        truncates = self.sweep.properties.averages[1]
        if truncates > 0 and averages > 1:
            logger.debug("Truncating %d values by %d",
                         len(values11), truncates)
            values11 = truncate(values11, truncates)
            values21 = truncate(values21, truncates)

        logger.debug("Averaging %d values", len(values11))
        values11 = np.average(values11, 0).tolist()
        values21 = np.average(values21, 0).tolist()

        return freq, values11, values21

    def readSegment(self, start, stop):
        logger.debug("Setting sweep range to %d to %d", start, stop)
        self.app.vna.setSweep(start, stop)

        frequencies = self.app.vna.readFrequencies()
        logger.debug("Read %s frequencies", len(frequencies))
        values11 = self.readData("data 0")
        values21 = self.readData("data 1")
        if not len(frequencies) == len(values11) == len(values21):
            logger.info("No valid data during this run")
            return [], [], []
        return frequencies, values11, values21

    def readData(self, data):
        logger.debug("Reading %s", data)
        done = False
        returndata = []
        count = 0
        while not done:
            done = True
            returndata = []
            tmpdata = self.app.vna.readValues(data)
            logger.debug("Read %d values", len(tmpdata))
            for d in tmpdata:
                a, b = d.split(" ")
                try:
                    if self.app.vna.validateInput and (
                            abs(float(a)) > 9.5 or
                            abs(float(b)) > 9.5):
                        logger.warning(
                            "Got a non plausible data value: (%s)", d)
                        done = False
                        break
                    returndata.append((float(a), float(b)))
                except ValueError as exc:
                    logger.exception("An exception occurred reading %s: %s",
                                     data, exc)
                    done = False
            if not done:
                logger.debug("Re-reading %s", data)
                sleep(0.2)
                count += 1
                if count == 5:
                    logger.error("Tried and failed to read %s %d times.",
                                 data, count)
                    logger.debug("trying to reconnect")
                    self.app.vna.reconnect()
                if count >= 10:
                    logger.critical(
                        "Tried and failed to read %s %d times. Giving up.",
                        data, count)
                    raise IOError(
                        f"Failed reading {data} {count} times.\n"
                        f"Data outside expected valid ranges,"
                        f" or in an unexpected format.\n\n"
                        f"You can disable data validation on the"
                        f"device settings screen.")
        return returndata

    def gui_error(self, message: str):
        self.error_message = message
        self.stopped = True
        self.running = False
        self.signals.sweepError.emit()

-- phpMyAdmin SQL Dump
-- version 5.0.4deb2+deb11u1
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Feb 25, 2025 at 02:16 PM
-- Server version: 10.5.26-MariaDB-0+deb11u2
-- PHP Version: 7.4.33

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `scanner`
--
CREATE DATABASE IF NOT EXISTS `scanner` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `scanner`;

-- --------------------------------------------------------

--
-- Table structure for table `periods`
--

CREATE TABLE `periods` (
  `period_ID` int(11) NOT NULL,
  `schedule_ID` int(11) NOT NULL,
  `block_val` char(1) NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `start_time` int(11) NOT NULL,
  `end_time` int(11) NOT NULL,
  `late_var` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `scans`
--

CREATE TABLE `scans` (
  `scan_ID` char(36) NOT NULL DEFAULT uuid(),
  `period_ID` int(11) NOT NULL,
  `schedule_ID` int(11) NOT NULL,
  `macID` varchar(30) NOT NULL,
  `scan_date` date NOT NULL,
  `scan_time` int(11) NOT NULL,
  `status` smallint(6) NOT NULL,
  `reason` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `schedules`
--

CREATE TABLE `schedules` (
  `schedule_ID` int(11) NOT NULL COMMENT 'Primary key, auto-incremented, uniquely identifies each schedule',
  `name` varchar(50) NOT NULL COMMENT 'Name of the schedule',
  `type` tinyint(4) NOT NULL COMMENT 'Type of schedule (block or traditional)',
  `absent_var` int(11) NOT NULL COMMENT 'Threshold (in minutes) for marking a student absent'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `schedule_days`
--

CREATE TABLE `schedule_days` (
  `schedule_ID` int(11) NOT NULL,
  `weekday` tinyint(4) NOT NULL,
  `dynamic_daytype` tinyint(1) NOT NULL DEFAULT 0,
  `daytype` char(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `student_names`
--

CREATE TABLE `student_names` (
  `macID` varchar(30) NOT NULL,
  `first_name` varchar(50) DEFAULT NULL,
  `last_name` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `student_periods`
--

CREATE TABLE `student_periods` (
  `macID` varchar(30) NOT NULL,
  `period_ID` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `system_control`
--

CREATE TABLE `system_control` (
  `master_pass` varchar(6) DEFAULT NULL COMMENT 'stores the master password',
  `timeout_time` int(11) NOT NULL DEFAULT 5,
  `active_schedule_ID` int(11) DEFAULT NULL COMMENT 'stores the schedule_ID of the active table'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `system_control`
--

INSERT INTO `system_control` (`master_pass`, `timeout_time`, `active_schedule_ID`) VALUES
('', 300, NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `periods`
--
ALTER TABLE `periods`
  ADD PRIMARY KEY (`period_ID`),
  ADD KEY `schedule deletion (periods)` (`schedule_ID`);

--
-- Indexes for table `scans`
--
ALTER TABLE `scans`
  ADD PRIMARY KEY (`scan_ID`),
  ADD KEY `schedule deletion (scans)` (`schedule_ID`),
  ADD KEY `period deletion (scans)` (`period_ID`),
  ADD KEY `student deletion (scans)` (`macID`);

--
-- Indexes for table `schedules`
--
ALTER TABLE `schedules`
  ADD PRIMARY KEY (`schedule_ID`);

--
-- Indexes for table `schedule_days`
--
ALTER TABLE `schedule_days`
  ADD KEY `schedule deletion (schedule_days)` (`schedule_ID`);

--
-- Indexes for table `student_names`
--
ALTER TABLE `student_names`
  ADD PRIMARY KEY (`macID`);

--
-- Indexes for table `student_periods`
--
ALTER TABLE `student_periods`
  ADD KEY `period deletion (student_periods)` (`period_ID`),
  ADD KEY `student deletion (student_periods)` (`macID`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `periods`
--
ALTER TABLE `periods`
  MODIFY `period_ID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=31;

--
-- AUTO_INCREMENT for table `schedules`
--
ALTER TABLE `schedules`
  MODIFY `schedule_ID` int(11) NOT NULL AUTO_INCREMENT COMMENT 'Primary key, auto-incremented, uniquely identifies each schedule', AUTO_INCREMENT=7;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `periods`
--
ALTER TABLE `periods`
  ADD CONSTRAINT `schedule deletion (periods)` FOREIGN KEY (`schedule_ID`) REFERENCES `schedules` (`schedule_ID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `scans`
--
ALTER TABLE `scans`
  ADD CONSTRAINT `period deletion (scans)` FOREIGN KEY (`period_ID`) REFERENCES `periods` (`period_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `schedule deletion (scans)` FOREIGN KEY (`schedule_ID`) REFERENCES `schedules` (`schedule_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `student deletion (scans)` FOREIGN KEY (`macID`) REFERENCES `student_names` (`macID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `schedule_days`
--
ALTER TABLE `schedule_days`
  ADD CONSTRAINT `schedule deletion (schedule_days)` FOREIGN KEY (`schedule_ID`) REFERENCES `schedules` (`schedule_ID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `student_periods`
--
ALTER TABLE `student_periods`
  ADD CONSTRAINT `period deletion (student_periods)` FOREIGN KEY (`period_ID`) REFERENCES `periods` (`period_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `student deletion (student_periods)` FOREIGN KEY (`macID`) REFERENCES `student_names` (`macID`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

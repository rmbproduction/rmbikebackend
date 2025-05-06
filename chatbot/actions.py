from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import random
import datetime

class ActionProvideBikeSpecificInfo(Action):
    """Provides bike-specific information based on detected bike type or part"""

    def name(self) -> Text:
        return "action_provide_bike_specific_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get slots
        bike_type = tracker.get_slot("bike_type")
        bike_part = tracker.get_slot("bike_part")
        
        # If bike type is known, provide specific information
        if bike_type:
            bike_type = bike_type.lower()
            
            if "mountain" in bike_type or "mtb" in bike_type:
                dispatcher.utter_message(text=f"For mountain bikes, we recommend more frequent maintenance checks, especially if you're riding rough trails. Our technicians are certified in servicing suspension systems and hydraulic components common on mountain bikes.")
            
            elif "road" in bike_type:
                dispatcher.utter_message(text=f"Road bikes benefit from regular drivetrain cleaning and tire inspections. Our mechanics are experts at dialing in the precise shifting and optimal tire pressure that make road riding enjoyable.")
            
            elif "electric" in bike_type or "e-bike" in bike_type or "ebike" in bike_type:
                dispatcher.utter_message(text=f"E-bikes require specialized knowledge to service properly. Our technicians are certified to work on major e-bike systems including Bosch, Shimano Steps, and Specialized Turbo, ensuring your battery and motor stay in optimal condition.")
            
            elif "gravel" in bike_type:
                dispatcher.utter_message(text=f"Gravel bikes take a beating from mixed terrain riding. We recommend regular drivetrain cleaning and bearing checks. Our mechanics can help set up the perfect tire pressure and component choices for your specific gravel adventures.")
            
            elif "kids" in bike_type or "children" in bike_type:
                dispatcher.utter_message(text=f"We take special care with children's bikes, focusing on safety and proper fit as they grow. Our safety inspections ensure brakes are easily operated by small hands and all components are secure.")
            
            else:
                dispatcher.utter_message(text=f"We have experience with all types of {bike_type} bikes. Our mechanics can provide specific maintenance recommendations during your service appointment.")
        
        # If bike part is known, provide specific information
        if bike_part:
            bike_part = bike_part.lower()
            
            if "brake" in bike_part:
                dispatcher.utter_message(text=f"Brake issues can be safety critical. Whether you have rim brakes or disc brakes, our technicians ensure they're properly adjusted for optimal stopping power and lever feel.")
            
            elif "suspension" in bike_part or "fork" in bike_part or "shock" in bike_part:
                dispatcher.utter_message(text=f"Suspension components require regular maintenance to perform their best. We offer everything from basic tuning to complete rebuilds, helping you get the most control and comfort from your suspension.")
            
            elif "wheel" in bike_part or "rim" in bike_part:
                dispatcher.utter_message(text=f"Wheel issues can affect everything from comfort to safety. Our wheel truing service restores proper alignment, and we can advise on upgrades or replacements if needed.")
            
            elif "tire" in bike_part or "tyre" in bike_part:
                dispatcher.utter_message(text=f"We offer both traditional and tubeless tire services. Proper tire choice and pressure make a huge difference in ride quality and puncture resistance.")
            
            elif "chain" in bike_part or "drivetrain" in bike_part or "cassette" in bike_part or "derailleur" in bike_part:
                dispatcher.utter_message(text=f"Drivetrain components directly impact shifting performance and efficiency. We can clean, adjust, or replace worn parts to keep your bike shifting smoothly and efficiently.")
            
            elif "bottom bracket" in bike_part or "bb" in bike_part:
                dispatcher.utter_message(text=f"Bottom bracket issues often present as creaking or resistance when pedaling. We can diagnose and repair these issues, which often require specialized tools and knowledge.")
            
            elif "electronic" in bike_part or "di2" in bike_part or "etap" in bike_part:
                dispatcher.utter_message(text=f"Electronic shifting systems require specialized knowledge. Our technicians are trained on the latest electronic groupsets including diagnostics, firmware updates, and component replacement.")
            
            else:
                dispatcher.utter_message(text=f"Our technicians are experienced with all aspects of {bike_part} service and repair. We'd be happy to take a look at yours.")
        
        return []

class ActionProvideMaintenanceSchedule(Action):
    """Provides personalized maintenance schedule recommendations"""

    def name(self) -> Text:
        return "action_provide_maintenance_schedule"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        bike_type = tracker.get_slot("bike_type")
        
        # Base maintenance schedule
        basic_schedule = {
            "Every ride": "Quick pre-ride check (ABC: Air, Brakes, Chain)",
            "Weekly": "Check tire pressure and chain lubrication",
            "Monthly": "Full cleaning and detailed inspection",
            "Quarterly": "Professional tune-up service"
        }
        
        # Tailored advice based on bike type
        if bike_type:
            bike_type = bike_type.lower()
            
            if "mountain" in bike_type:
                additional_advice = "For mountain bikes ridden on rough terrain, we recommend more frequent suspension checks and pivot maintenance. After muddy rides, a thorough cleaning is essential to prevent premature wear."
            
            elif "road" in bike_type:
                additional_advice = "For road bikes, pay special attention to tire wear and pressure. Check for embedded debris after each ride to prevent flats. A professional drivetrain deep clean every 1,000 miles helps maintain crisp shifting."
            
            elif "electric" in bike_type or "e-bike" in bike_type:
                additional_advice = "For e-bikes, keep your battery at 30-80% charge when storing for more than a few days. Have a diagnostic check of your motor system annually to ensure optimal performance and battery life."
            
            elif "commuter" in bike_type:
                additional_advice = "For daily commuters, weekly chain maintenance and quarterly professional services are essential. Watch for brake pad wear closely, as commuting in traffic demands reliable stopping power."
            
            else:
                additional_advice = "Regular maintenance keeps your bike safe and extends its life. Our technicians can create a custom maintenance schedule based on your specific riding habits."
        else:
            additional_advice = "The right maintenance schedule depends on your riding style, frequency, and conditions. Our technicians can help create a personalized plan when you bring your bike in."
        
        # Create maintenance message
        maintenance_message = "Here's a recommended maintenance schedule:\n\n"
        for period, task in basic_schedule.items():
            maintenance_message += f"🔸 {period}: {task}\n"
        
        maintenance_message += f"\n{additional_advice}"
        
        dispatcher.utter_message(text=maintenance_message)
        
        return []

class ActionSuggestAppointmentTimes(Action):
    """Suggests available appointment times"""

    def name(self) -> Text:
        return "action_suggest_appointment_times"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the requested date slot if it exists
        requested_date = tracker.get_slot("appointment_date")
        service_type = tracker.get_slot("service_type")
        
        # Mock function to simulate checking availability
        # In a real implementation, this would check a database
        def get_available_times(date_str=None, service=None):
            # Simulate some available times
            morning = ["9:00 AM", "10:30 AM", "11:15 AM"]
            afternoon = ["1:00 PM", "2:30 PM", "4:15 PM"]
            
            # For demo purposes, remove some times based on service type
            if service and "overhaul" in service.lower():
                # Overhauls take longer, so fewer slots
                return morning[:1] + afternoon[:1]
            elif service and ("tune" in service.lower() or "adjustment" in service.lower()):
                # Standard services have most slots
                return morning + afternoon
            else:
                # Default availability
                return morning + afternoon[:2]
        
        # Get available times
        available_times = get_available_times(requested_date, service_type)
        
        # Create a human-readable date for the message
        if requested_date:
            try:
                # Try to parse the date in a flexible way
                # This is a simplified example - in production you'd use more robust date parsing
                if "tomorrow" in requested_date.lower():
                    readable_date = "tomorrow"
                elif "next" in requested_date.lower() and "week" in requested_date.lower():
                    readable_date = "next week"
                elif "weekend" in requested_date.lower():
                    readable_date = "this weekend"
                else:
                    readable_date = requested_date
                
                date_message = f"for {readable_date}"
            except:
                date_message = ""
        else:
            date_message = "in the near future"
        
        # Construct the message
        if service_type:
            service_message = f"for your {service_type}"
        else:
            service_message = "for your service"
        
        # Format the message
        if available_times:
            times_str = ", ".join(available_times)
            message = f"I checked our availability {date_message} {service_message}, and we have openings at: {times_str}. Would any of these times work for you?"
        else:
            message = f"It looks like we don't have any immediate availability {date_message} {service_message}. I'd recommend calling our shop directly at (555) 123-4567 to discuss options."
        
        dispatcher.utter_message(text=message)
        
        return []

class ActionEstimateRepairCost(Action):
    """Provides rough cost estimates for common repairs"""

    def name(self) -> Text:
        return "action_estimate_repair_cost"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get slots
        bike_part = tracker.get_slot("bike_part")
        problem = tracker.get_slot("problem")
        bike_type = tracker.get_slot("bike_type")
        
        # Default message if we can't determine specific repair
        default_message = "The cost of repairs varies depending on the specific issue and parts needed. For an accurate estimate, we'd need to inspect your bike. Our basic inspection is free, and we always provide a quote before proceeding with any work."
        
        # If we have enough information, provide a rough estimate
        if bike_part and problem:
            bike_part = bike_part.lower()
            problem = problem.lower()
            
            # Price estimates for common repairs - would be from a database in production
            estimates = {
                "flat tire": "$25-35 depending on tire/tube quality",
                "tube replacement": "$25-35 depending on tire/tube quality",
                "brake adjustment": "$35-45",
                "brake replacement": "$45-85 depending on brake type",
                "gear adjustment": "$35-50",
                "chain replacement": "$45-85 depending on chain quality",
                "wheel truing": "$30-45",
                "bottom bracket replacement": "$75-150 depending on BB type",
                "derailleur adjustment": "$35-45",
                "derailleur replacement": "$75-180 depending on component level",
                "bearing service": "$50-120 depending on location and condition",
                "hydraulic brake bleed": "$45-65 per brake",
                "suspension service": "$85-250 depending on service level and suspension type"
            }
            
            # Try to match the problem to our known estimates
            estimate = None
            
            # Check for flat tire scenarios
            if ("tire" in bike_part or "wheel" in bike_part) and ("flat" in problem or "puncture" in problem):
                estimate = estimates["flat tire"]
            
            # Check for brake issues
            elif "brake" in bike_part:
                if any(term in problem for term in ["adjust", "loose", "tight", "rubbing", "squeaking"]):
                    estimate = estimates["brake adjustment"]
                elif any(term in problem for term in ["replace", "broken", "not working"]):
                    estimate = estimates["brake replacement"]
                elif "bleed" in problem or "spongy" in problem:
                    estimate = estimates["hydraulic brake bleed"]
            
            # Check for drivetrain issues
            elif any(part in bike_part for part in ["gear", "shift", "derailleur"]):
                if any(term in problem for term in ["adjust", "tune", "skip", "clicking"]):
                    estimate = estimates["gear adjustment"]
                elif any(term in problem for term in ["replace", "broken", "bent"]):
                    estimate = estimates["derailleur replacement"]
            
            # Check for chain issues
            elif "chain" in bike_part:
                if "replace" in problem or "worn" in problem or "stretched" in problem:
                    estimate = estimates["chain replacement"]
            
            # Check for wheel issues
            elif "wheel" in bike_part:
                if "wobble" in problem or "true" in problem or "bent" in problem:
                    estimate = estimates["wheel truing"]
            
            # Check for bottom bracket issues
            elif "bottom bracket" in bike_part or "bb" in bike_part or "crank" in bike_part:
                if any(term in problem for term in ["creak", "grinding", "rough", "play", "loose"]):
                    estimate = estimates["bottom bracket replacement"]
            
            # Check for suspension issues
            elif "suspension" in bike_part or "fork" in bike_part or "shock" in bike_part:
                if any(term in problem for term in ["service", "rebuild", "leaking", "stiff", "sticky"]):
                    estimate = estimates["suspension service"]
            
            # If we found a matching estimate
            if estimate:
                message = f"Based on your description of an issue with the {bike_part} {problem}, the estimated cost would be around {estimate}. This is just a rough estimate - we can provide an exact quote after inspecting your bike."
            else:
                message = f"For your {bike_part} issue described as '{problem}', we'd need to inspect it for an accurate quote. Many basic adjustments start at $35, while repairs involving replacement parts vary based on the components needed."
        else:
            message = default_message
        
        dispatcher.utter_message(text=message)
        
        # Add a follow-up about booking if appropriate
        if bike_part and problem:
            dispatcher.utter_message(text="Would you like to schedule a time to bring your bike in for inspection and repair?")
        
        return [] 